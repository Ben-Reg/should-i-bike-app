async function evaluateRules(dateStr, departureHour, returnHour, settings) {
  const { zip, country, hoursReturned } = settings;
  const rules = await getRulesWithGroups();
  let score = 0;
  const relevantRules = [];

  for (const rule of rules) {
    const hour = rule.tripTime === 'Return' ? returnHour : departureHour;
    let ruleResult = true;

    for (const group of rule.groups) {
      let groupResult;

      if (group.operator === 'AND') {
        groupResult = true;
        for (const el of group.elements) {
          const pass = await evaluateElement(el, dateStr, hour, settings);
          if (!pass) { groupResult = false; break; }
        }
      } else {
        groupResult = false;
        for (const el of group.elements) {
          const pass = await evaluateElement(el, dateStr, hour, settings);
          if (pass) { groupResult = true; break; }
        }
      }

      if (!groupResult) { ruleResult = false; break; }
    }

    if (ruleResult) {
      score += Number(rule.weight);
      relevantRules.push(rule);
    }
  }

  return { score, bike: score < 10, relevantRules };
}

async function evaluateElement(element, dateStr, hour, settings) {
  const { zip, country, hoursReturned } = settings;
  const val = await getForecastValue(element.weatherElement, dateStr, hour, zip, country, hoursReturned);
  if (val === null) return false;

  const op = element.operator;
  const target = element.value;

  if (op === '>=')          return val >= Number(target);
  if (op === '<=')          return val <= Number(target);
  if (op === '>')           return val > Number(target);
  if (op === '<')           return val < Number(target);
  if (op === '=')           return String(val) === String(target);
  if (op === '!=')          return String(val) !== String(target);
  if (op === 'CONTAINS')    return String(val).includes(target);
  if (op === 'NOT CONTAINS') return !String(val).includes(target);
  return false;
}
