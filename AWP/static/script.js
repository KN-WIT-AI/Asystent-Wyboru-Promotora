async function renderQueryResult(query) {
  const result = await fetch("/api/zapytanie", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ zapytanie: query }),
  });

  const data = await result.json();

  const renderedChildren = data.error
    ? ErrorText(data.error)
    : // Take only top 3 supervisors - this should be done on the backend
      SupervisorsList(data.results.slice(0, 3));

  return renderedChildren;
}

async function handleForm(e) {
  e.preventDefault();
  const query = document.getElementById("query").value;
  const resultsDiv = document.getElementById("results");

  try {
    resultsDiv.replaceChildren(await renderQueryResult(query));
  } catch (error) {
    console.error(error);
    resultsDiv.replaceChildren(
      ErrorText("Wystąpił błąd podczas przetwarzania zapytania.")
    );
  }
}

document.getElementById("queryForm").addEventListener("submit", handleForm);
