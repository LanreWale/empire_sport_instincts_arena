// EMPIRE SPORT INSTINCTS ARENA - Premium Chart Rendering

// Bankroll Evolution Chart
document.addEventListener('DOMContentLoaded', function() {
    const bankrollCtx = document.getElementById('bankrollChart');
    if (bankrollCtx) {
        const dates = [];
        const bankroll = [];
        let current = 10000;

        for (let i = 30; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            dates.push(date.toLocaleDateString());
            current = current * (1 + (Math.random() * 0.02 - 0.005));
            bankroll.push(current);
        }

        new Chart(bankrollCtx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Bankroll ($)',
                    data: bankroll,
                    borderColor: '#FFD700',
                    backgroundColor: 'rgba(212, 175, 55, 0.15)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#D4AF37',
                    pointBorderColor: '#FFD700',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { 
                            color: '#e0e0e0',
                            font: { weight: 'bold' }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1a1a2e',
                        titleColor: '#FFD700',
                        bodyColor: '#e0e0e0',
                        borderColor: '#D4AF37',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#888' },
                        grid: { color: '#333' }
                    },
                    y: {
                        ticks: { 
                            color: '#888',
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        grid: { color: '#333' }
                    }
                }
            }
        });
    }

    // Monthly Performance Chart
    const monthlyCtx = document.getElementById('monthlyChart');
    if (monthlyCtx) {
        new Chart(monthlyCtx, {
            type: 'bar',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                datasets: [{
                    label: 'Profit ($)',
                    data: [120, 95, -45, 180, 70],
                    backgroundColor: [
                        'rgba(212, 175, 55, 0.8)',
                        'rgba(212, 175, 55, 0.8)',
                        'rgba(255, 68, 68, 0.8)',
                        'rgba(212, 175, 55, 0.8)',
                        'rgba(212, 175, 55, 0.8)'
                    ],
                    borderColor: [
                        '#D4AF37',
                        '#D4AF37',
                        '#FF4444',
                        '#D4AF37',
                        '#D4AF37'
                    ],
                    borderWidth: 2,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { 
                            color: '#e0e0e0',
                            font: { weight: 'bold' }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1a1a2e',
                        titleColor: '#FFD700',
                        bodyColor: '#e0e0e0',
                        borderColor: '#D4AF37',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#888' },
                        grid: { color: '#333' }
                    },
                    y: {
                        ticks: { 
                            color: '#888',
                            callback: function(value) {
                                return '$' + value;
                            }
                        },
                        grid: { color: '#333' }
                    }
                }
            }
        });
    }

    // Sport Breakdown Doughnut Chart (if element exists)
    const sportCtx = document.getElementById('sportChart');
    if (sportCtx) {
        new Chart(sportCtx, {
            type: 'doughnut',
            data: {
                labels: ['Football', 'NBA', 'NFL', 'Tennis'],
                datasets: [{
                    data: [45, 32, 28, 15],
                    backgroundColor: [
                        'rgba(212, 175, 55, 0.8)',
                        'rgba(255, 215, 0, 0.8)',
                        'rgba(184, 134, 11, 0.8)',
                        'rgba(192, 192, 192, 0.8)'
                    ],
                    borderColor: [
                        '#D4AF37',
                        '#FFD700',
                        '#B8860B',
                        '#C0C0C0'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { 
                            color: '#e0e0e0',
                            font: { weight: 'bold' }
                        }
                    }
                }
            }
        });
    }
});
