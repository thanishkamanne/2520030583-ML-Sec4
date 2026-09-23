const form = document.getElementById("predictionForm");
const predictBtn = document.getElementById("predictBtn");
const btnText = predictBtn.querySelector(".btn-text");
const spinner = predictBtn.querySelector(".spinner");
const resultContent = document.getElementById("resultContent");
const emptyResult = document.getElementById("emptyResult");
const resultBadge = document.getElementById("resultBadge");

document.getElementById("demoBtn").addEventListener("click", () => {
  document.getElementById("date").value = "2004-08-05";
  document.getElementById("timestamp").value = "16.01638";
  document.getElementById("direction").value = "south";
  document.getElementById("day_night").value = "day";
  document.getElementById("weather").value = "overcast";
  document.getElementById("start_frame").value = "2";
  document.getElementById("number_of_frames").value = "53";
});

form.addEventListener("reset", () => {
  setTimeout(() => {
    resultContent.classList.add("hidden");
    emptyResult.classList.remove("hidden");
    resultBadge.textContent = "Waiting";
    resultBadge.className = "result-badge idle";
  }, 0);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!form.reportValidity()) return;

  const data = {
    date: document.getElementById("date").value,
    timestamp: document.getElementById("timestamp").value,
    direction: document.getElementById("direction").value,
    day_night: document.getElementById("day_night").value,
    weather: document.getElementById("weather").value,
    start_frame: document.getElementById("start_frame").value,
    number_of_frames: document.getElementById("number_of_frames").value
  };

  predictBtn.disabled = true;
  btnText.style.display = "none";
  spinner.style.display = "block";

  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data)
    });
    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(result.error || "Prediction failed");
    }

    showResult(result);
  } catch (error) {
    alert(error.message);
  } finally {
    predictBtn.disabled = false;
    btnText.style.display = "inline";
    spinner.style.display = "none";
  }
});

function showResult(result) {
  emptyResult.classList.add("hidden");
  resultContent.classList.remove("hidden");
  resultBadge.textContent = "Prediction complete";
  resultBadge.className = "result-badge live";

  document.getElementById("predictionValue").textContent = result.traffic_class;
  document.getElementById("confidenceValue").textContent = result.confidence + "%";
  document.getElementById("confidenceBar").style.width = Math.min(result.confidence, 100) + "%";

  const order = ["light", "medium", "heavy"];
  const probList = document.getElementById("probList");
  probList.innerHTML = "";

  order.forEach(cls => {
    const value = result.probabilities[cls] ?? 0;
    probList.innerHTML += `
      <div class="prob-row">
        <span>${cls.charAt(0).toUpperCase() + cls.slice(1)}</span>
        <div class="bar"><div style="width:${value}%"></div></div>
        <b>${value}%</b>
      </div>`;
  });

  const summaryGrid = document.getElementById("summaryGrid");
  summaryGrid.innerHTML = "";
  Object.entries(result.inputs).forEach(([key, value]) => {
    summaryGrid.innerHTML += `<div class="summary-item"><span>${key}</span><b>${value}</b></div>`;
  });
}
