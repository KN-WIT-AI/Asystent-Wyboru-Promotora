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

        // Take only top 3 supervisors
        const topResults = data.results.slice(0, 3);

        resultsDiv.innerHTML = `
            <h2>Najlepsze dopasowania:</h2>
            ${topResults
                .map((supervisor, index) => `
                    <div class="supervisor-result">
                        <h3>#${index + 1} ${supervisor.supervisor}</h3>
                        <p>Średnia odległość: ${Number.parseFloat(supervisor.average_score).toFixed(4)}</p>
                        
                        ${supervisor.top_interests.length > 0 ? `
                            <h4>Dopasowane zainteresowania:</h4>
                            <ul>
                                ${supervisor.top_interests
                                    .map(interest => `<li>${interest}</li>`)
                                    .join('')}
                            </ul>
                        ` : ''}
                        
                        ${supervisor.top_papers.length > 0 ? `
                            <h4>Dopasowane prace:</h4>
                            <ul>
                                ${supervisor.top_papers
                                    .map(paper => `<li>${paper}</li>`)
                                    .join('')}
                            </ul>
                        ` : ''}
                    </div>
                    ${index < topResults.length - 1 ? '<hr>' : ''}
                `)
                .join("")}
        `;

    } catch (error) {
        console.error('Error:', error);
        resultsDiv.innerHTML = `<p class="error">Wystąpił błąd podczas przetwarzania zapytania.</p>`;
    }
}

document.getElementById('queryForm').addEventListener('submit', handleForm);