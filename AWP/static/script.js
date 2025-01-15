function createHeaderedList(headerText, items) {
  const container = document.createElement("div");
  const header = document.createElement("h4");
  header.innerText = headerText;

  const itemsList = createList(items);

  container.appendChild(header);
  container.appendChild(itemsList);

  return container;
}

function createList(items) {
  const itemsList = document.createElement("ul");
  for (let item of items) {
    const li = document.createElement("li");
    li.innerText = item;
    itemsList.appendChild(li);
  }
  return itemsList;
}

function createSupervisorCard(index, supervisor) {
  const supervisorDiv = document.createElement("div");
  supervisorDiv.classList.add("supervisor-result");

  const header = document.createElement("h3");
  header.innerText = `#${index} ${supervisor.supervisor}`;

  const avgScore = document.createElement("p");
  avgScore.innerText = `Średnia odległość: ${Number.parseFloat(
    supervisor.average_score
  ).toFixed(4)}`;

  supervisorDiv.appendChild(header);
  supervisorDiv.appendChild(avgScore);

  if (supervisor.top_interests.length > 0) {
    const interests = createHeaderedList(
      "Dopasowane zainteresowania:",
      supervisor.top_interests
    );
    supervisorDiv.appendChild(interests);
  }

  if (supervisor.top_papers.length > 0) {
    const papers = createHeaderedList(
      "Dopasowane prace:",
      supervisor.top_papers
    );
    supervisorDiv.appendChild(papers);
  }

  return supervisorDiv;
}

function handleSupervisorsResult(supervisors) {
  // Take only top 3 supervisors
  const topResults = supervisors.slice(0, 3);
  const result = document.createElement("div");

  const header = document.createElement("h2");
  header.innerText = "Najlepsze dopasowania:";

  result.appendChild(header);

  let index = 0;
  for (let supervisor of topResults) {
    const supervisorDiv = createSupervisorCard(++index, supervisor);
    result.appendChild(supervisorDiv);
  }

  return result;
}

async function handleForm(e) {
  e.preventDefault();
  const query = document.getElementById("query").value;

  const result = await fetch("/api/zapytanie", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ zapytanie: query }),
  });

  const data = await result.json();
  const resultsDiv = document.getElementById("results");

  try {
    if (data.error) {
      resultsDiv.innerHTML = `<p class="error">${data.error}</p>`;
      return;
    }

    resultsDiv.replaceChildren(handleSupervisorsResult(data.results));
  } catch (error) {
    console.error("Error:", error);
    resultsDiv.innerHTML = `<p class="error">Wystąpił błąd podczas przetwarzania zapytania.</p>`;
  }
}

document.getElementById("queryForm").addEventListener("submit", handleForm);
