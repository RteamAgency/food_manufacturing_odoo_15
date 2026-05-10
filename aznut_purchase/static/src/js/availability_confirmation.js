odoo.define('aznut_purchase.availability_confirmation', function () {
    "use strict";

    $(document).ready(function () {
        const rows = document.querySelectorAll("tbody.aznut_website tr[data-line-id]:not([data-line-id^='remainder'])"),
            order = document.querySelector("input[name='order_id']"),
            orderId = order ? order.value : undefined,
            commentsBlock = document.querySelector(".aznut_purchase-comments"),
            submitButton = document.querySelector(".aznut_purchase-submit");

        function handleStatusChange(select) {
            const row = select.closest('tr');
            const quantityInput = row.querySelector('.aznut_purchase-quantity');
            const originalQty = parseFloat(quantityInput.dataset.originalQty);

            if (select.value === 'out') {
                quantityInput.value = '0.00';
                quantityInput.readOnly = true;
            } else {
                quantityInput.value = originalQty.toFixed(2);
                quantityInput.readOnly = false;
            }
            validateAllRows();
        }

        function handleRemainderStatusChange(select) {
            validateAllRows();
        }

        function validateAllRows() {
            let allValid = true;

            rows.forEach(row => {
                const quantityInput = row.querySelector('.aznut_purchase-quantity');
                const dateInput = row.querySelector('.aznut_purchase-date');
                const status = row.querySelector('.aznut_purchase-status');
                const originalQty = parseFloat(quantityInput.dataset.originalQty);
                const currentQty = parseFloat(quantityInput.value || '0');
                const lineId = row.dataset.lineId;
                const remainderRow = document.querySelector(`tr[data-line-id='remainder-${lineId}']`);
                const remainderQtyInput = remainderRow?.querySelector('.aznut_purchase-remainder-qty');
                const remainderDateInput = remainderRow?.querySelector('.aznut_purchase-remainder-date');
                const remainderStatus = remainderRow?.querySelector('.aznut_purchase-remainder-status');
                quantityInput.classList.remove('is-invalid');
                dateInput.classList.remove('is-invalid');
                remainderDateInput?.classList.remove('is-invalid');

                if (status.value === 'in') {
                    if (!dateInput.value) {
                        dateInput.classList.add('is-invalid');
                        allValid = false;
                    }
                    if (
                        isNaN(currentQty) ||
                        currentQty > originalQty ||
                        currentQty < 0 ||
                        currentQty === 0
                    ) {
                        quantityInput.classList.add('is-invalid');
                        allValid = false;
                    }
                }
                if (status.value === 'in' && currentQty < originalQty && currentQty >= 0) {
                    const remainderQty = (originalQty - currentQty).toFixed(2);
                    remainderRow.style.display = '';
                    remainderQtyInput.value = remainderQty;

                    if (remainderStatus.value === 'in') {
                        if (!remainderDateInput.value) {
                            remainderDateInput.classList.add('is-invalid');
                            allValid = false;
                        }
                    }

                } else {
                    if (remainderRow) {
                        remainderRow.style.display = 'none';
                        remainderQtyInput.value = '';
                        remainderDateInput.value = '';
                    }
                }
            });

            submitButton.style.display = allValid ? 'inline-block' : 'none';
        }

        function aznutPurchaseSubmitForm(rows, orderId, commentsBlock) {
            const lines = [],
                comments = commentsBlock ? commentsBlock.value : undefined;

            rows.forEach(row => {
                const lineId = row.dataset.lineId;
                const quantity = row.querySelector(".aznut_purchase-quantity").value;
                const date = row.querySelector(".aznut_purchase-date").value;
                const status = row.querySelector(".aznut_purchase-status").value;

                const remainderRow = document.querySelector(`tr[data-line-id='remainder-${lineId}']`);
                const remainderQty = remainderRow?.querySelector('.aznut_purchase-remainder-qty')?.value || null;
                const remainderDate = remainderRow?.querySelector('.aznut_purchase-remainder-date')?.value || null;
                const remainderStatus = remainderRow?.querySelector('.aznut_purchase-remainder-status')?.value || null;

                lines.push({
                    id: lineId,
                    qty: quantity,
                    date: date,
                    status: status,
                    remainder_qty: remainderQty,
                    remainder_date: remainderDate,
                    remainder_status: remainderStatus
                });
            });

            fetch("/confirm/availability", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": odoo.csrf_token
                },
                body: JSON.stringify({
                    order: orderId,
                    comments: comments,
                    lines: lines
                })
            })
                .then(response => response.json())
                .then(data => {
                    alert(data.result.message);
                    location.reload();
                })
                .catch(err => {
                    console.error("Error submitting form:", err);
                });
        }

        document.querySelectorAll('.aznut_purchase-status').forEach(select => {
            select.addEventListener('change', () => handleStatusChange(select));
            handleStatusChange(select);
        });
        document.querySelectorAll('.aznut_purchase-remainder-status').forEach(select => {
            select.addEventListener('change', () => handleRemainderStatusChange(select));
        });
        document.querySelectorAll('.aznut_purchase-quantity').forEach(input => {
            input.addEventListener('input', validateAllRows);
            input.addEventListener('blur', () => {
                const value = parseFloat(input.value);
                if (!isNaN(value)) input.value = value.toFixed(2);
            });
        });
        document.querySelectorAll('.aznut_purchase-date, .aznut_purchase-remainder-date').forEach(input => {
            input.addEventListener('input', validateAllRows);
        });
        document.querySelectorAll('.aznut_purchase-submit').forEach(button => {
            button.addEventListener('click', () => aznutPurchaseSubmitForm(rows, orderId, commentsBlock));
        });
        if (rows.length > 0) validateAllRows();
    });
});
