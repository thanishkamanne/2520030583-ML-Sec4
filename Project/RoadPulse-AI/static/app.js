const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('videoInput');
const dropzone = document.getElementById('dropzone');
const fileTitle = document.getElementById('fileTitle');
const fileSubtitle = document.getElementById('fileSubtitle');
const previewWrap = document.getElementById('previewWrap');
const videoPreview = document.getElementById('videoPreview');
const analyzeBtn = document.getElementById('analyzeBtn');
const progressWrap = document.getElementById('progressWrap');
const errorBox = document.getElementById('errorBox');
const outputPanel = document.getElementById('outputPanel');
let previewUrl = null;

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  fileTitle.textContent = file.name;
  fileSubtitle.textContent = `${(file.size / (1024 * 1024)).toFixed(1)} MB · Ready to analyze`;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  videoPreview.src = previewUrl;
  previewWrap.classList.remove('hidden');
  errorBox.classList.add('hidden');
});
['dragenter', 'dragover'].forEach(eventName => dropzone.addEventListener(eventName, e => {
  e.preventDefault(); dropzone.classList.add('dragover');
}));
['dragleave', 'drop'].forEach(eventName => dropzone.addEventListener(eventName, e => {
  e.preventDefault(); dropzone.classList.remove('dragover');
}));
dropzone.addEventListener('drop', e => {
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer(); transfer.items.add(file); fileInput.files = transfer.files;
  fileInput.dispatchEvent(new Event('change'));
});

form.addEventListener('submit', async e => {
  e.preventDefault();
  errorBox.classList.add('hidden');
  const file = fileInput.files[0];
  if (!file) return showError('Please choose a road video first.');
  if (file.size > 200 * 1024 * 1024) return showError('This file is larger than 200 MB. Please choose a shorter or smaller video.');
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['mp4', 'avi', 'mov', 'mkv', 'webm'].includes(ext)) return showError('Unsupported video format. Use MP4, AVI, MOV, MKV, or WEBM.');

  const body = new FormData(); body.append('video', file);
  analyzeBtn.disabled = true;
  analyzeBtn.querySelector('span:first-child').textContent = 'Analyzing video…';
  progressWrap.classList.remove('hidden');
  outputPanel.classList.add('hidden');
  document.getElementById('progressText').textContent = 'Loading AI detector and analyzing sampled frames…';
  try {
    const response = await fetch('/analyze', { method: 'POST', body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis failed. Please try another video.');
    renderResults(data);
  } catch (err) {
    showError(err.message || 'Could not analyze this video.');
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.querySelector('span:first-child').textContent = 'Run AI analysis';
    progressWrap.classList.add('hidden');
  }
});

function showError(message) { errorBox.textContent = message; errorBox.classList.remove('hidden'); }
function renderResults(data) {
  document.getElementById('metricVehicles').textContent = data.total_unique_vehicles;
  document.getElementById('metricDensity').textContent = data.density;
  document.getElementById('metricPeak').textContent = data.peak_visible;
  document.getElementById('metricDuration').textContent = `${data.duration_seconds}s`;
  document.getElementById('countCar').textContent = data.vehicle_counts.Car;
  document.getElementById('countMoto').textContent = data.vehicle_counts.Motorcycle;
  document.getElementById('countBus').textContent = data.vehicle_counts.Bus;
  document.getElementById('countTruck').textContent = data.vehicle_counts.Truck;
  const alertCard = document.getElementById('alertCard');
  alertCard.className = `alert-card ${data.alert_type === 'warning' ? 'warning' : data.alert_type === 'good' ? 'good' : ''}`;
  document.getElementById('alertTitle').textContent = data.alert_type === 'warning' ? 'Congestion build-up signal' : data.alert_type === 'good' ? 'Traffic easing signal' : 'Traffic activity signal';
  document.getElementById('alertText').textContent = data.alert;
  document.getElementById('resultHeading').textContent = data.filename || 'Video analysis results';
  document.getElementById('resultSubheading').textContent = document.getElementById('cameraName').value.trim() || 'Annotated output and traffic signals from your clip.';
  const videoUrl = `${data.video_url}?t=${Date.now()}`;
  const resultVideo = document.getElementById('resultVideo'); resultVideo.src = videoUrl; resultVideo.load();
  const download = document.getElementById('downloadVideo'); download.href = data.video_url; download.download = `roadpulse-${Date.now()}.mp4`;
  const badge = document.getElementById('densityBadge'); badge.className = `density-badge ${data.severity === 'medium' ? 'medium' : data.severity === 'high' ? 'heavy' : ''}`;
  document.getElementById('resultDensity').textContent = `${data.density} traffic`;
  document.getElementById('resultExplanation').textContent = data.explanation;
  document.getElementById('resultAverage').textContent = data.average_visible;
  document.getElementById('resultPeak').textContent = data.peak_visible;
  document.getElementById('resultFrames').textContent = data.processed_frames;
  document.getElementById('resultTrend').textContent = data.alert_type === 'warning' ? 'Increasing' : data.alert_type === 'good' ? 'Decreasing' : 'No strong change';
  document.getElementById('methodNote').textContent = data.method_note;
  drawTimeline(data.timeline || []);
  outputPanel.classList.remove('hidden');
  outputPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function drawTimeline(points) {
  const chart = document.getElementById('timelineChart'); chart.innerHTML = '';
  if (!points.length) { chart.innerHTML = '<span class="chart-empty">No timeline data available</span>'; return; }
  const max = Math.max(1, ...points.map(p => p.visible));
  points.forEach(point => {
    const bar = document.createElement('div'); bar.className = 'bar';
    bar.style.height = `${Math.max(4, (point.visible / max) * 100)}%`;
    bar.title = `${point.seconds}s: ${point.visible} visible vehicles`;
    chart.appendChild(bar);
  });
}
