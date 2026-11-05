const scenario = document.getElementById("scenario");
const scenarioData = JSON.parse(document.getElementById("scenario-data").textContent);
const description = document.getElementById("scenario-description");
scenario.addEventListener("change", () => {
  description.textContent = scenarioData[scenario.value] || "";
});
