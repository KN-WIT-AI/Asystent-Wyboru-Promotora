async function handleForm(e) {
    e.preventDefault();
    const query = document.getElementById('query').value;

    const result = await fetch('/api/zapytanie', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ zapytanie: query })
    });

    const data = await result.json();

    const resultsDiv = document.getElementById('results');

    try {
        if (data.error) {
            resultsDiv.innerHTML = `<p class="error">${data.error}</p>`;
            return;
        }

        resultsDiv.innerHTML = data.results
            .map(x => `
                <p>
                    <div>${x.supervisor}</div>
                    <div>${x.zainteresowanie}</div>
                    <div>${Number.parseFloat(x.Odległość).toFixed(2)} jw</div>
                </p>`
            )
            .join("");

    } catch (error) {
        console.error('Error:', error);
        resultsDiv.innerHTML = `<p class="error">Wystąpił błąd podczas przetwarzania zapytania.</p>`;
    }
}

document.getElementById('queryForm').addEventListener('submit', handleForm);