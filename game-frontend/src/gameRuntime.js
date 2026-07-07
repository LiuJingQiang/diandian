export const OPERATORS = {
  0: (a, b) => a === b,
  1: (a, b) => a !== b,
  2: (a, b) => a > b,
  3: (a, b) => a >= b,
  4: (a, b) => a < b,
  5: (a, b) => a <= b,
};

export function operand(vars, item) {
  if (!item) return 0;
  if (item.vType === 3) return item.str || '';
  if (item.name === 'const') return Number(item.num) || 0;
  if (item.name === 'random') return Math.floor(Math.random() * 10) + 1;
  if (!item.name && item.str) return item.str;
  return vars[item.name] ?? (Number(item.num) || 0);
}

export function applyHandlers(vars, handlers = []) {
  const next = { ...vars };
  for (const handler of handlers || []) {
    if (!handler.var || !handler.list?.length) continue;
    let acc = operand(next, handler.list[0]);
    for (let i = 1; i < handler.list.length; i += 1) {
      const right = operand(next, handler.list[i]);
      const op = (handler.ops || [])[i - 1] || '+';
      if (typeof acc === 'string' || typeof right === 'string') acc = `${acc}${right}`;
      else if (op === '-') acc -= right;
      else if (op === '*') acc *= right;
      else if (op === '/') acc = right ? acc / right : acc;
      else acc += right;
    }
    next[handler.var] = typeof acc === 'number' ? Math.round(acc) : acc;
  }
  return next;
}

export function conditionPass(vars, condition) {
  const compare = OPERATORS[condition.op] || OPERATORS[0];
  let right;
  if (condition.right?.length) right = condition.right.reduce((sum, item) => sum + operand(vars, item), 0);
  else if (condition.target !== '' && condition.target != null) {
    const parsed = Number(condition.target);
    right = Number.isNaN(parsed) ? condition.target : parsed;
  } else return true;
  let left = condition.left?.length
    ? condition.left.reduce((sum, item) => sum + operand(vars, item), 0)
    : vars[condition.var] ?? 0;
  if (typeof right === 'string') left = String(vars[condition.var] ?? '');
  return compare(left, right);
}

export function conditionsPass(vars, conditions = [], relation = 'and') {
  if (!conditions?.length) return true;
  const results = conditions.map((condition) => conditionPass(vars, condition));
  return relation === 'or' ? results.some(Boolean) : results.every(Boolean);
}

export function fillText(vars, text = '') {
  const hero = vars['主角名字'];
  return hero ? text.replaceAll('主角名字', hero) : text;
}

export function initialVars(story) {
  return Object.fromEntries((story.variables || []).map((key) => [key, 0]));
}

export function firstVisibleChat(node, vars) {
  return (node.chats || []).findIndex((chat) => conditionsPass(vars, chat.conditions));
}
