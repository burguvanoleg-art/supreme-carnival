document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('queryInput');
    const askBtn = document.getElementById('askBtn');
    const btnText = askBtn.querySelector('.btn-text');
    const spinner = askBtn.querySelector('.spinner');
    const resultsContainer = document.getElementById('results');
    const weatherContent = document.getElementById('weatherContent');
    const placesContent = document.getElementById('placesContent');
    const recommendationContent = document.getElementById('recommendationContent');
    const errorBox = document.getElementById('errorBox');

    const setLoading = (isLoading) => {
        askBtn.disabled = isLoading;
        if (isLoading) {
            btnText.classList.add('hidden');
            spinner.classList.remove('hidden');
            resultsContainer.classList.add('hidden');
            errorBox.classList.add('hidden');
        } else {
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    };

    const showError = (message) => {
        errorBox.textContent = message;
        errorBox.classList.remove('hidden');
    };

    const handleSearch = async () => {
        const query = queryInput.value.trim();
        if (!query) return;

        setLoading(true);

        try {
            const response = await fetch(`/advisor?query=${encodeURIComponent(query)}`);
            const result = await response.json();

            if (result.status === 'ok') {
                const { weather, places_found, featured_venue, recommendation, metadata, missing_city } = result.data;

                if (missing_city) {
                    recommendationContent.innerHTML = `<div class="recommendation-text">${recommendation}</div>`;
                    resultsContainer.classList.remove('hidden');
                    weatherContent.innerHTML = '<p class="text-muted">Please provide a city for weather data.</p>';
                    placesContent.innerHTML = '<p class="text-muted">Please provide a city for venue search.</p>';
                    return;
                }

                // Update Weather
                weatherContent.innerHTML = `
                    <div class="weather-info">
                        <div class="temp-row">
                            <span>🌡️ ${weather.max_temp}°C / ${weather.min_temp}°C</span>
                        </div>
                        <div class="rain-chance">
                            🌧️ ${weather.rain_chance}% chance of rain
                        </div>
                        <div class="place-addr">${metadata.city} on ${metadata.date}</div>
                    </div>
                `;

                // Update Places
                let allPlaces = [...(places_found || [])];
                if (featured_venue) {
                    // Add AI featured venue at the top if not already there
                    const exists = allPlaces.some(p => p.name.toLowerCase() === featured_venue.name.toLowerCase());
                    if (!exists) {
                        allPlaces.unshift({ ...featured_venue, isFeatured: true });
                    }
                }

                if (allPlaces.length > 0) {
                    placesContent.innerHTML = `
                        <ul class="places-list">
                            ${allPlaces.map(p => {
                                const mapQuery = encodeURIComponent(`${p.name}, ${p.address}, ${metadata.city}`);
                                const mapUrl = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;
                                return `
                                    <li class="place-item ${p.isFeatured ? 'featured-item' : ''}">
                                        <span class="place-name">📍 ${p.name} ${p.isFeatured ? '<small>(AI Pick)</small>' : ''}</span>
                                        <a href="${mapUrl}" target="_blank" class="place-addr" title="Open in Google Maps">
                                            ${p.address} 🔗
                                        </a>
                                    </li>
                                `;
                            }).join('')}
                        </ul>
                    `;
                } else {
                    placesContent.innerHTML = '<p class="text-muted">No specific venues found nearby.</p>';
                }

                // Update Recommendation
                recommendationContent.innerHTML = `
                    <div class="recommendation-text">${recommendation.replace(/\n/g, '<br>')}</div>
                `;

                resultsContainer.classList.remove('hidden');
            } else {
                showError(result.data || 'Failed to get recommendation');
            }
        } catch (error) {
            console.error('Fetch error:', error);
            showError('Network error. Please make sure the server is running.');
        } finally {
            setLoading(false);
        }
    };

    askBtn.addEventListener('click', handleSearch);

    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
});
