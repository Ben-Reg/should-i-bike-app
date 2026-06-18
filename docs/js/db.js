const db = new Dexie('should-i-bike');

db.version(1).stores({
  rule_types: '++id, name, weather_element',
  rules: '++id, name, trip_time, weight',
  settings: '++id, name, value, description',
  rule_groups: '++id, rule_id, operator',
  rule_group_elements: '++id, rule_group_id, rule_type_id, operator, value',
  weather_cache: 'key, data, timestamp'
});

async function seedDefaults() {
  const rtCount = await db.rule_types.count();
  if (rtCount === 0) {
    await db.rule_types.bulkAdd([
      { name: 'Temperature',   weather_element: 'temperature' },
      { name: 'Wind Speed',    weather_element: 'windSpeed' },
      { name: 'Wind Direction',weather_element: 'windDirection' },
      { name: 'Wind Gust',     weather_element: 'windGust' },
      { name: 'Visibility',    weather_element: 'visibility' },
      { name: 'Rain Chance',   weather_element: 'probabilityOfPrecipitation' },
    ]);
  }
  const sCount = await db.settings.count();
  if (sCount === 0) {
    await db.settings.bulkAdd([
      { name: 'Zip',               value: '67114', description: 'Zip code for the weather forecast' },
      { name: 'Country',           value: 'US',    description: 'Country code (US only currently)' },
      { name: 'Default Departure', value: '7',     description: 'Default departure time (0-24)' },
      { name: 'Default Return',    value: '17',    description: 'Default return time (0-24)' },
      { name: 'Hours Returned',    value: '48',    description: 'Number of hours in the forecast view' },
    ]);
  }
}

async function loadSettings() {
  const rows = await db.settings.toArray();
  const out = {};
  for (const r of rows) {
    out[r.name] = { id: r.id, value: r.value, description: r.description };
  }
  return out;
}

async function updateSetting(name, value) {
  const row = await db.settings.where('name').equals(name).first();
  if (row) await db.settings.update(row.id, { value: String(value) });
}

async function getRuleTypes() {
  return db.rule_types.toArray();
}

async function loadRules() {
  return db.rules.orderBy('name').toArray();
}

async function saveRule(rule) {
  return db.rules.add({ name: rule.name, trip_time: rule.tripTime, weight: Number(rule.weight) });
}

async function editRule(id, rule) {
  return db.rules.update(id, { name: rule.name, trip_time: rule.tripTime, weight: Number(rule.weight) });
}

async function deleteRule(id) {
  const groups = await db.rule_groups.where('rule_id').equals(id).toArray();
  for (const g of groups) await deleteRuleGroup(g.id);
  await db.rules.delete(id);
}

async function loadRuleGroups(ruleId) {
  const groups = await db.rule_groups.where('rule_id').equals(ruleId).toArray();
  for (const g of groups) {
    const elements = await db.rule_group_elements.where('rule_group_id').equals(g.id).toArray();
    for (const e of elements) {
      const rt = await db.rule_types.get(e.rule_type_id);
      e.typeName = rt ? rt.name : '';
      e.weatherElement = rt ? rt.weather_element : '';
    }
    g.elements = elements;
  }
  return groups;
}

async function saveRuleGroup(ruleId, operator) {
  return db.rule_groups.add({ rule_id: ruleId, operator });
}

async function editRuleGroup(id, operator) {
  return db.rule_groups.update(id, { operator });
}

async function deleteRuleGroup(id) {
  await db.rule_group_elements.where('rule_group_id').equals(id).delete();
  await db.rule_groups.delete(id);
}

async function createGroupElement(groupId, ruleTypeId, operator, value) {
  return db.rule_group_elements.add({ rule_group_id: groupId, rule_type_id: ruleTypeId, operator, value });
}

async function editGroupElement(id, ruleTypeId, operator, value) {
  return db.rule_group_elements.update(id, { rule_type_id: ruleTypeId, operator, value });
}

async function deleteGroupElement(id) {
  return db.rule_group_elements.delete(id);
}

async function getRulesWithGroups() {
  const rules = await db.rules.toArray();
  for (const rule of rules) {
    const groups = await db.rule_groups.where('rule_id').equals(rule.id).toArray();
    for (const g of groups) {
      const elements = await db.rule_group_elements.where('rule_group_id').equals(g.id).toArray();
      for (const e of elements) {
        const rt = await db.rule_types.get(e.rule_type_id);
        e.weatherElement = rt ? rt.weather_element : '';
      }
      g.elements = elements;
    }
    rule.tripTime = rule.trip_time;
    rule.groups = groups;
  }
  return rules;
}

async function exportRulesData() {
  const rules = await db.rules.toArray();
  const out = [];
  for (const rule of rules) {
    const groups = await db.rule_groups.where('rule_id').equals(rule.id).toArray();
    const groupsOut = [];
    for (const g of groups) {
      const elements = await db.rule_group_elements.where('rule_group_id').equals(g.id).toArray();
      const elemsOut = [];
      for (const e of elements) {
        const rt = await db.rule_types.get(e.rule_type_id);
        if (!rt) continue;
        elemsOut.push({ rule_type: rt.name, operator: e.operator, value: e.value });
      }
      groupsOut.push({ operator: g.operator, elements: elemsOut });
    }
    out.push({ name: rule.name, trip_time: rule.trip_time, weight: rule.weight, groups: groupsOut });
  }
  return out;
}

async function importRulesData(rules) {
  const allTypes = await db.rule_types.toArray();
  const typeMap = {};
  for (const rt of allTypes) typeMap[rt.name] = rt.id;

  let imported = 0;
  const warnings = [];

  for (const ruleData of rules) {
    const ruleId = await db.rules.add({
      name:      ruleData.name,
      trip_time: ruleData.trip_time,
      weight:    Number(ruleData.weight)
    });

    for (const groupData of (ruleData.groups || [])) {
      const groupId = await db.rule_groups.add({ rule_id: ruleId, operator: groupData.operator });

      for (const elemData of (groupData.elements || [])) {
        const rtId = typeMap[elemData.rule_type];
        if (rtId === undefined) {
          warnings.push(`Rule '${ruleData.name}': unknown rule_type '${elemData.rule_type}' skipped`);
          continue;
        }
        await db.rule_group_elements.add({
          rule_group_id: groupId,
          rule_type_id:  rtId,
          operator:      elemData.operator,
          value:         String(elemData.value)
        });
      }
    }
    imported++;
  }

  return { imported, warnings };
}
