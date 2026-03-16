document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let currentStep = 1;
    let wizardData = {
        city: '',
        date: '',
        venue: '',
        intent: ''
    };

    // --- DOM Elements ---
    const steps = {
        1: document.getElementById('step1'),
        2: document.getElementById('step2'),
        3: document.getElementById('step3'),
        4: document.getElementById('step4'),
        result: document.getElementById('resultStep')
    };
    const stepDescription = document.getElementById('stepDescription');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const errorBox = document.getElementById('errorBox');

    // Inputs
    const cityInput = document.getElementById('cityInput');
    const intentInput = document.getElementById('intentInput');

    // Containers
    const forecastContainer = document.getElementById('forecastContainer');
    const venuesContainer = document.getElementById('venuesContainer');
    const displayCity = document.getElementById('displayCity');
    const recommendationText = document.getElementById('recommendationText');

    // --- Helpers ---
    const showStep = (step) => {
        Object.values(steps).forEach(el => el.classList.add('hidden'));
        if (step === 'result') {
            steps.result.classList.remove('hidden');
            stepDescription.textContent = "Your personalized plan is ready!";
        } else {
            steps[step].classList.remove('hidden');
            updateStepDescription(step);
        }
        currentStep = step;
        errorBox.classList.add('hidden');
    };

    const updateStepDescription = (step) => {
        const desc = {
            1: "Step 1: Choose your destination",
            2: "Step 2: Pick a day from the forecast",
            3: "Step 3: Explore popular venues",
            4: "Step 4: Tell us what you'd like to do"
        };
        stepDescription.textContent = desc[step];
    };

    const toggleLoading = (show) => {
        loadingOverlay.classList.toggle('hidden', !show);
    };

    const showError = (msg) => {
        errorBox.textContent = msg;
        errorBox.classList.remove('hidden');
        toggleLoading(false);
    };

    // --- Actions ---

    const handleCityNext = async () => {
        const city = cityInput.value.trim();
        if (!city) return;

        toggleLoading(true);
        try {
            const res = await fetch(`/city-forecast?city_name=${encodeURIComponent(city)}`);
            const result = await res.json();

            if (result.status === 'ok') {
                wizardData.city = result.data.city;
                displayCity.textContent = result.data.city;
                renderForecast(result.data.forecast);
                showStep(2);
            } else {
                showError(result.data);
            }
        } catch (err) {
            showError("Failed to fetch city data.");
        } finally {
            toggleLoading(false);
        }
    };

    const renderForecast = (forecast) => {
        forecastContainer.innerHTML = '';
        forecast.forEach(day => {
            const card = document.createElement('div');
            card.className = 'forecast-card';
            card.innerHTML = `
                <div class="forecast-date">${new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
                <div class="forecast-temp">${day.max_temp}°C</div>
                <div class="forecast-rain">🌧️ ${day.rain_chance}%</div>
            `;
            card.onclick = () => {
                wizardData.date = day.date;
                document.querySelectorAll('.forecast-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                handleForecastNext();
            };
            forecastContainer.appendChild(card);
        });
    };

    const handleForecastNext = async () => {
        toggleLoading(true);
        try {
            const res = await fetch(`/popular-venues?city_name=${encodeURIComponent(wizardData.city)}`);
            const result = await res.json();

            if (result.status === 'ok') {
                renderVenues(result.data);
                showStep(3);
            } else {
                showError("Could not find popular venues.");
            }
        } catch (err) {
            showError("Error fetching venues.");
        } finally {
            toggleLoading(false);
        }
    };

    const renderVenues = (venues) => {
        venuesContainer.innerHTML = '';
        if (venues.length === 0) {
            venuesContainer.innerHTML = '<p class="text-muted">No specific popular venues found.</p>';
            return;
        }
        venues.forEach(v => {
            const card = document.createElement('div');
            card.className = 'venue-card';
            card.innerHTML = `
                <span class="venue-type">${v.type}</span>
                <span class="venue-name">${v.name}</span>
                <small class="text-muted">${v.address}</small>
            `;
            card.onclick = () => {
                wizardData.venue = v.name;
                document.querySelectorAll('.venue-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
            };
            venuesContainer.appendChild(card);
        });
    };

    const handleFinalAdvice = async () => {
        const intent = intentInput.value.trim();
        if (!intent) return;
        wizardData.intent = intent;

        toggleLoading(true);
        try {
            const url = `/wizard-advisor?city=${encodeURIComponent(wizardData.city)}&date=${wizardData.date}&intent=${encodeURIComponent(wizardData.intent)}&venue=${encodeURIComponent(wizardData.venue)}`;
            const res = await fetch(url);
            const result = await res.json();

            if (result.status === 'ok') {
                recommendationText.innerHTML = result.data.recommendation.replace(/\n/g, '<br>');
                showStep('result');
            } else {
                showError(result.data);
            }
        } catch (err) {
            showError("Failed to generate recommendation.");
        } finally {
            toggleLoading(false);
        }
    };

    // --- Events ---
    document.getElementById('cityNextBtn').onclick = handleCityNext;
    document.getElementById('venueNextBtn').onclick = () => showStep(4);
    document.getElementById('finalNextBtn').onclick = handleFinalAdvice;
    document.getElementById('restartBtn').onclick = () => {
        cityInput.value = '';
        intentInput.value = '';
        wizardData = { city: '', date: '', venue: '', intent: '' };
        showStep(1);
    };

    document.querySelectorAll('.backBtn').forEach(btn => {
        btn.onclick = () => {
            if (currentStep > 1) showStep(currentStep - 1);
        };
    });

    cityInput.onkeypress = (e) => { if (e.key === 'Enter') handleCityNext(); };
    intentInput.onkeypress = (e) => { if (e.key === 'Enter') handleFinalAdvice(); };
});
