/**
 * NEEPCO Procurement and Vendor Payment Data Portal
 * Client-Side JavaScript Enhancements
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Mobile Sidebar Toggle
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebar = document.getElementById('sidebar');

    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function (event) {
            if (window.innerWidth < 992) {
                if (!sidebar.contains(event.target) && !sidebarToggleBtn.contains(event.target)) {
                    sidebar.classList.remove('show');
                }
            }
        });
    }

    // 2. Real-time Payment Calculator (in Add/Edit Payment modal or form)
    const invAmountInput = document.getElementById('invoice_amount');
    const paidAmountInput = document.getElementById('amount_paid');
    const outstandingPreview = document.getElementById('outstanding_preview');
    const statusPreview = document.getElementById('status_preview');

    function updatePaymentCalculations() {
        if (!invAmountInput) return;
        const inv = parseFloat(invAmountInput.value) || 0;
        const paid = parseFloat(paidAmountInput ? paidAmountInput.value : 0) || 0;
        const outstanding = Math.max(0, inv - paid);

        if (outstandingPreview) {
            outstandingPreview.textContent = '₹ ' + outstanding.toLocaleString('en-IN', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }

        if (statusPreview) {
            let status = 'Pending';
            let badgeClass = 'badge-pending';

            if (paid >= inv && inv > 0) {
                status = 'Paid';
                badgeClass = 'badge-paid';
            } else if (paid > 0 && paid < inv) {
                status = 'Partially Paid';
                badgeClass = 'badge-partial';
            }

            statusPreview.textContent = status;
            statusPreview.className = 'badge-status ' + badgeClass;
        }
    }

    if (invAmountInput && paidAmountInput) {
        invAmountInput.addEventListener('input', updatePaymentCalculations);
        paidAmountInput.addEventListener('input', updatePaymentCalculations);
        updatePaymentCalculations();
    }

    // 3. Password match validation on registration form
    const regForm = document.getElementById('registerForm');
    if (regForm) {
        regForm.addEventListener('submit', function (e) {
            const pass = document.getElementById('password').value;
            const confirmPass = document.getElementById('confirm_password').value;
            if (pass !== confirmPass) {
                e.preventDefault();
                alert('Passwords do not match. Please verify.');
                document.getElementById('confirm_password').focus();
            }
        });
    }
});
