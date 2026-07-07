export const characterStage = {
  jimuzhou: { preferred: 'left' },
  bailing: { preferred: 'right' },
  hanzhao: { preferred: 'right' },
  luqingluo: { preferred: 'left' },
  tongque: { preferred: 'right' },
  zuizhong: { position: 'center', artOnly: true },
};

export const stagingRules = {
  alternateDifferentConsecutiveCharacters: true,
  defaultLeadPosition: 'left',
  defaultSecondaryPosition: 'right',
};

export function oppositeSide(position) {
  return position === 'left' ? 'right' : 'left';
}

export function resolveStageMeta(characterId, character, previousStage) {
  const base = characterStage[characterId] || {
    preferred: character?.lead ? stagingRules.defaultLeadPosition : stagingRules.defaultSecondaryPosition,
  };

  if (base.position) return base;

  const shouldAlternate = stagingRules.alternateDifferentConsecutiveCharacters
    && previousStage?.charId
    && previousStage.charId !== characterId;

  return {
    ...base,
    position: shouldAlternate
      ? oppositeSide(previousStage.position)
      : previousStage?.position || base.preferred || stagingRules.defaultSecondaryPosition,
  };
}
