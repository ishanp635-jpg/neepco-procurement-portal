/**
 * NEEPCO Procurement and Vendor Payment Data Portal
 * Dashboard Charts Renderer using Chart.js
 */

document.addEventListener('DOMContentLoaded', function () {
    const typeCanvas = document.getElementById('chartProcurementType');
    const mseCanvas = document.getElementById('chartMseShare');
    const gemCanvas = document.getElementById('chartGemStatus');
    const paymentCanvas = document.getElementById('chartPaymentStatus');

    if (!typeCanvas) return; // Not on dashboard page

    // Fetch dynamic chart data from Flask API
    fetch('/api/dashboard-charts')
        .then(response => response.json())
        .then(data => {
            renderCharts(data);
        })
        .catch(err => {
            console.error('Error fetching dashboard chart data:', err);
        });

    function formatCurrencyTooltip(value) {
        return '₹ ' + Number(value).toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function renderCharts(data) {
        // Chart 1: Procurement by Category/Type (Bar Chart)
        new Chart(typeCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.procurement_by_type.labels,
                datasets: [{
                    label: 'Procurement Amount (INR)',
                    data: data.procurement_by_type.values,
                    backgroundColor: [
                        '#0b2545',
                        '#1976d2',
                        '#06b6d4',
                        '#8b5cf6'
                    ],
                    borderRadius: 6,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ' Amount: ' + formatCurrencyTooltip(ctx.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) {
                                if (val >= 10000000) return '₹' + (val / 10000000).toFixed(1) + ' Cr';
                                if (val >= 100000) return '₹' + (val / 100000).toFixed(1) + ' L';
                                if (val >= 1000) return '₹' + (val / 1000).toFixed(0) + ' k';
                                return '₹' + val;
                            }
                        },
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });

        // Chart 2: MSE vs Non-MSE Procurement (Doughnut Chart)
        new Chart(mseCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.mse_vs_non_mse.labels,
                datasets: [{
                    data: data.mse_vs_non_mse.values,
                    backgroundColor: ['#10b981', '#cbd5e1'],
                    hoverOffset: 4,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, padding: 15, font: { size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ' ' + ctx.label + ': ' + formatCurrencyTooltip(ctx.raw);
                            }
                        }
                    }
                }
            }
        });

        // Chart 3: GeM Orders by Status (Bar Chart)
        new Chart(gemCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.gem_by_status.labels,
                datasets: [{
                    label: 'Order Value (INR)',
                    data: data.gem_by_status.values,
                    backgroundColor: [
                        '#10b981',
                        '#0284c7',
                        '#f59e0b',
                        '#64748b',
                        '#ef4444'
                    ],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ' Value: ' + formatCurrencyTooltip(ctx.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) {
                                if (val >= 100000) return '₹' + (val / 100000).toFixed(1) + ' L';
                                return '₹' + val;
                            }
                        },
                        grid: { color: '#f1f5f9' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });

        // Chart 4: Paid vs Pending Payments (Doughnut Chart)
        new Chart(paymentCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.payment_status.labels,
                datasets: [{
                    data: data.payment_status.values,
                    backgroundColor: ['#10b981', '#ef4444'],
                    hoverOffset: 4,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, padding: 15, font: { size: 12 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ' ' + ctx.label + ': ' + formatCurrencyTooltip(ctx.raw);
                            }
                        }
                    }
                }
            }
        });
    }
});
