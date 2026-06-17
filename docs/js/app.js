const { createApp, ref, computed, onMounted, watch } = Vue;

createApp({
  setup() {
    // ── routing ──────────────────────────────────────────────────────────────
    const route = ref(location.hash.replace('#', '') || '/');
    const routeParams = ref({});

    function navigate(path, params = {}) {
      const m = path.match(/^\/rules\/(\d+)$/);
      if (m) {
        route.value = '/rules/:id';
        routeParams.value = { id: Number(m[1]) };
      } else {
        route.value = path;
        routeParams.value = params;
      }
      location.hash = path;
    }

    window.addEventListener('hashchange', () => {
      const h = location.hash.replace('#', '') || '/';
      const m = h.match(/^\/rules\/(\d+)$/);
      if (m) { route.value = '/rules/:id'; routeParams.value = { id: Number(m[1]) }; }
      else    { route.value = h; routeParams.value = {}; }
    });

    // ── global state ─────────────────────────────────────────────────────────
    const settings   = ref({});
    const ruleTypes  = ref([]);
    const loading    = ref(false);
    const error      = ref('');

    async function loadGlobals() {
      await seedDefaults();
      settings.value  = await loadSettings();
      ruleTypes.value = await getRuleTypes();
    }

    // ── home screen ──────────────────────────────────────────────────────────
    const tomorrow = (() => {
      const d = new Date(); d.setDate(d.getDate() + 1);
      return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    })();

    const selectedDate      = ref(tomorrow);
    const departureHour     = ref(7);
    const returnHour        = ref(17);
    const result            = ref(null);
    const travelConditions  = ref(null);

    watch(settings, s => {
      if (s['Default Departure']) departureHour.value = Number(s['Default Departure'].value);
      if (s['Default Return'])    returnHour.value    = Number(s['Default Return'].value);
    }, { deep: true });

    async function checkBike() {
      error.value = '';
      loading.value = true;
      try {
        const s = {
          zip:          settings.value['Zip']?.value || '67114',
          country:      settings.value['Country']?.value || 'US',
          hoursReturned: Number(settings.value['Hours Returned']?.value || 48),
        };
        result.value = await evaluateRules(selectedDate.value, Number(departureHour.value), Number(returnHour.value), s);

        // Build travel conditions display
        const dep = await buildConditions(selectedDate.value, Number(departureHour.value), s);
        const ret = await buildConditions(selectedDate.value, Number(returnHour.value), s);
        travelConditions.value = { departure: dep, return: ret };

        navigate('/result');
      } catch(e) {
        error.value = e.message || 'Failed to fetch weather data.';
      } finally {
        loading.value = false;
      }
    }

    async function buildConditions(dateStr, hour, s) {
      const elements = ['temperature','windSpeed','windDirection','windGust','probabilityOfPrecipitation','visibility'];
      const labels   = ['Temp (°F)','Wind Speed (mph)','Wind Dir','Wind Gust (mph)','Rain Chance (%)','Visibility (yds)'];
      const out = [];
      for (let i = 0; i < elements.length; i++) {
        const v = await getForecastValue(elements[i], dateStr, hour, s.zip, s.country, s.hoursReturned);
        out.push({ label: labels[i], value: v ?? '—' });
      }
      return out;
    }

    // ── forecast screen ──────────────────────────────────────────────────────
    const forecast = ref([]);

    async function loadForecast() {
      loading.value = true; error.value = '';
      try {
        const s = {
          zip:          settings.value['Zip']?.value || '67114',
          country:      settings.value['Country']?.value || 'US',
          hoursReturned: Number(settings.value['Hours Returned']?.value || 48),
        };
        const { forecast: f } = await getWeather(s.zip, s.country, s.hoursReturned);
        forecast.value = f;
      } catch(e) { error.value = e.message; }
      finally    { loading.value = false; }
    }

    function formatTime(iso) {
      const d = new Date(iso);
      return d.toLocaleString([], { weekday:'short', month:'numeric', day:'numeric', hour:'numeric', minute:'2-digit' });
    }

    // ── rules screen ─────────────────────────────────────────────────────────
    const rules = ref([]);

    async function loadRulesList() {
      rules.value = await loadRules();
    }

    // ── rule detail screen ───────────────────────────────────────────────────
    const currentRule   = ref(null);
    const ruleGroups    = ref([]);
    const editRuleModal = ref(false);
    const editRuleForm  = ref({ name: '', tripTime: 'Departure', weight: 0 });

    async function loadRuleDetail(id) {
      const all = await loadRules();
      currentRule.value = all.find(r => r.id === id) || null;
      ruleGroups.value  = await loadRuleGroups(id);
    }

    async function submitEditRule() {
      if (!currentRule.value) return;
      await editRule(currentRule.value.id, editRuleForm.value);
      await loadRuleDetail(currentRule.value.id);
      await loadRulesList();
      editRuleModal.value = false;
    }

    async function submitDeleteRule(id) {
      if (!confirm('Delete this rule and all its groups/elements?')) return;
      await deleteRule(id);
      await loadRulesList();
      navigate('/rules');
    }

    // groups
    const groupModal = ref(false);
    const groupForm  = ref({ id: null, operator: 'AND' });

    async function submitGroup() {
      if (groupForm.value.id) {
        await editRuleGroup(groupForm.value.id, groupForm.value.operator);
      } else {
        await saveRuleGroup(currentRule.value.id, groupForm.value.operator);
      }
      await loadRuleDetail(currentRule.value.id);
      groupModal.value = false;
    }

    async function submitDeleteGroup(id) {
      if (!confirm('Delete this group and its elements?')) return;
      await deleteRuleGroup(id);
      await loadRuleDetail(currentRule.value.id);
    }

    // elements
    const elementModal = ref(false);
    const elementForm  = ref({ id: null, groupId: null, ruleTypeId: null, operator: '>=', value: '' });
    const operators    = ['=','!=','>','>=','<','<=','CONTAINS','NOT CONTAINS'];

    async function openAddElement(groupId) {
      elementForm.value = { id: null, groupId, ruleTypeId: ruleTypes.value[0]?.id || null, operator: '>=', value: '' };
      elementModal.value = true;
    }

    async function openEditElement(el, groupId) {
      const rt = ruleTypes.value.find(t => t.weather_element === el.weatherElement);
      elementForm.value = { id: el.id, groupId, ruleTypeId: rt?.id || null, operator: el.operator, value: el.value };
      elementModal.value = true;
    }

    async function submitElement() {
      const { id, groupId, ruleTypeId, operator, value } = elementForm.value;
      if (id) {
        await editGroupElement(id, ruleTypeId, operator, value);
      } else {
        await createGroupElement(groupId, ruleTypeId, operator, value);
      }
      await loadRuleDetail(currentRule.value.id);
      elementModal.value = false;
    }

    async function submitDeleteElement(id) {
      if (!confirm('Delete this element?')) return;
      await deleteGroupElement(id);
      await loadRuleDetail(currentRule.value.id);
    }

    // new rule
    const newRuleModal = ref(false);
    const newRuleForm  = ref({ name: '', tripTime: 'Departure', weight: 0 });

    async function submitNewRule() {
      const id = await saveRule(newRuleForm.value);
      await loadRulesList();
      newRuleModal.value = false;
      navigate('/rules/' + id, { id });
    }

    // ── settings screen ──────────────────────────────────────────────────────
    const settingsForm = ref({});

    async function loadSettingsForm() {
      const s = await loadSettings();
      settingsForm.value = {};
      for (const [k, v] of Object.entries(s)) {
        settingsForm.value[k] = { ...v };
      }
    }

    async function saveSettings() {
      for (const [name, s] of Object.entries(settingsForm.value)) {
        await updateSetting(name, s.value);
      }
      settings.value = await loadSettings();
      await clearWeatherCache();
      error.value = '';
      alert('Settings saved. Weather cache cleared.');
    }

    // ── route watcher ─────────────────────────────────────────────────────────
    watch(route, async (r) => {
      error.value = '';
      if (r === '/forecast')  await loadForecast();
      if (r === '/rules')     await loadRulesList();
      if (r === '/rules/:id') await loadRuleDetail(routeParams.value.id);
      if (r === '/settings')  await loadSettingsForm();
    });

    onMounted(async () => {
      await loadGlobals();
      // Trigger initial route side-effects
      const h = location.hash.replace('#', '') || '/';
      const m = h.match(/^\/rules\/(\d+)$/);
      if (m) { route.value = '/rules/:id'; routeParams.value = { id: Number(m[1]) }; await loadRuleDetail(Number(m[1])); }
      else if (h === '/forecast') await loadForecast();
      else if (h === '/rules')    await loadRulesList();
      else if (h === '/settings') await loadSettingsForm();
    });

    return {
      route, routeParams, navigate,
      settings, ruleTypes, loading, error,
      // home
      selectedDate, departureHour, returnHour, result, travelConditions, checkBike, tomorrow,
      // forecast
      forecast, formatTime,
      // rules list
      rules,
      // rule detail
      currentRule, ruleGroups,
      editRuleModal, editRuleForm, submitEditRule, submitDeleteRule,
      groupModal, groupForm, submitGroup, submitDeleteGroup,
      elementModal, elementForm, operators, openAddElement, openEditElement, submitElement, submitDeleteElement,
      newRuleModal, newRuleForm, submitNewRule,
      // settings
      settingsForm, saveSettings,
    };
  }
}).mount('#app');
