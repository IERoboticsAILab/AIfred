document.querySelectorAll('.comparison-frame').forEach((frame) => {
  const slider = frame.querySelector('input[type="range"]');
  slider.addEventListener('input', () => {
    frame.style.setProperty('--split', `${slider.value}%`);
  });
});
