odoo.define('aznut_purchase.request_for_vendor', function () {
    'use strict';

    $(document).ready(function () {
        const form = document.getElementById('request-for-vendor-form');
        const submitBtn = document.querySelector('.request-for-vendor-submit');
        const rows = document.querySelectorAll('#request-for-vendor-form tbody tr');

        if (!form || !submitBtn || rows.length === 0) return;

        function validateDateFields() {
            let allValid = true;

            rows.forEach(row => {
                const dateInput = row.querySelector('.request-for-vendor-date');
                dateInput.classList.remove('is-invalid');

                if (!dateInput || !dateInput.value) {
                    dateInput.classList.add('is-invalid');
                    allValid = false;
                }
            });

            submitBtn.style.display = allValid ? 'inline-block' : 'none';
        }

        rows.forEach(row => {
            const dateInput = row.querySelector('.request-for-vendor-date');
            if (dateInput) {
                dateInput.addEventListener('input', validateDateFields);
            }
        });

        validateDateFields();

        submitBtn.addEventListener('click', function () {
            if (submitBtn.style.display !== 'none') {
                form.submit();
            }
        });
    });
});
