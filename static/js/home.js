(function () {
  'use strict';

  var defaultConfig = {
    header_text: 'Увесь досвід людства з вивчення англійської у твоїй кишені',
    block1_title: 'Чат-репетитор',
    block1_desc: 'Розмовляй за текстом, цитуй граматику',
    block1_badge: '✨ Активно',
    block2_title: 'Голосовий репетитор',
    block2_desc: 'Говори з AI в реальному часі',
    block2_badge: '🎤 Голосовий режим',
    block3_title: 'AI Персонаж',
    block3_desc: 'Повне занурення у світ англійської',
    block3_badge: '🤖 AI Персонаж'
  };

  function applyConfig(config) {
    var c = config || defaultConfig;
    var header = document.getElementById('headerText');
    if (header) header.textContent = c.header_text;

    var pairs = [
      ['block1Title', 'block1_title'],
      ['block1Desc', 'block1_desc'],
      ['block1Badge', 'block1_badge'],
      ['block2Title', 'block2_title'],
      ['block2Desc', 'block2_desc'],
      ['block2Badge', 'block2_badge'],
      ['block3Title', 'block3_title'],
      ['block3Desc', 'block3_desc'],
      ['block3Badge', 'block3_badge']
    ];
    for (var i = 0; i < pairs.length; i++) {
      var el = document.getElementById(pairs[i][0]);
      if (el && c[pairs[i][1]] !== undefined) el.textContent = c[pairs[i][1]];
    }
  }

  if (document.body && document.body.classList.contains('page-home')) {
    applyConfig(defaultConfig);
  }
})();
