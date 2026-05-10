odoo.define('aznut_portal.portal', function (require) {
    "use strict";

    const ajax = require('web.ajax');

    $(document).ready(function () {
        const qtyInput = document.getElementById("qty_data"),
            quantityInput = document.querySelector(".quantity-input"),
            availableQuantities = document.querySelectorAll(".available-quantity"),
            deliveryOrderFileData = document.getElementById("delivery_order_file_data"),
            duplicateQtyData = document.getElementById("duplicate_qty_data"),
            addToCart = document.getElementById("add_to_cart"),
            savedInput = document.getElementById('delivery_order_file_data_saved');


        if (qtyInput) {
            qtyInput.addEventListener("input", function () {
                const orderId = document.getElementById("order_input").value;
                ajax.jsonRpc('/get_qty_to_add', 'call', {
                    'order_id': orderId,
                    'qty_data': this.value
                }).then(function (result) {
                    if (result) {
                        let data = result['data'];
                        document.getElementById("output_span_orders").textContent = Object.keys(data).map(function (key) {
                            return `${key}: ${data[key]}`;
                        }).join(', ');
                    }
                });
                document.getElementById("output_span").textContent = this.value;
                document.getElementById("output_input_hidden").value = this.value;
            });
        }

        if (quantityInput && availableQuantities.length > 0) {
            function getTotalAvailableQuantity() {
                let total = 0;
                availableQuantities.forEach(el => {
                    total += parseFloat(el.getAttribute("data-available-quantity") || 0);
                });
                return total;
            }

            quantityInput.addEventListener("input", function () {
                const enteredValue = parseFloat(quantityInput.value) || 0;
                const totalAvailable = getTotalAvailableQuantity();
                const submitBtn = document.querySelector('.sale-order-submit-btn');

                if (enteredValue > totalAvailable) {
                    quantityInput.style.color = "red";
                    if (submitBtn) submitBtn.style.display = 'none';
                } else {
                    quantityInput.style.color = "";
                    if (submitBtn) {
                        submitBtn.style.display = enteredValue ? 'block' : 'none';
                    }
                }
            });
        }

        if (deliveryOrderFileData && savedInput) {
            deliveryOrderFileData.addEventListener('change', function () {
                const fileNameDisplay = document.getElementById('delivery-order-file-name');
                const dataTransfer = new DataTransfer();  // Create DataTransfer to manage the files
                const newFiles = this.files;
                for (let i = 0; i < savedInput.files.length; i++) {
                    dataTransfer.items.add(savedInput.files[i]);
                }
                for (let i = 0; i < newFiles.length; i++) {
                    dataTransfer.items.add(newFiles[i]);
                }
                savedInput.files = dataTransfer.files;
                const changeEvent = new Event('change', {
                    bubbles: true,
                    cancelable: true,
                });
                savedInput.dispatchEvent(changeEvent);
                for (let i = 0; i < newFiles.length; i++) {
                    const listItem = document.createElement('div');
                    const fileIndex = fileNameDisplay.childElementCount + 1;
                    listItem.textContent = `${fileIndex}. ${newFiles[i].name} `;
                    const deleteButton = document.createElement('a');
                    deleteButton.textContent = '×';
                    deleteButton.style.marginLeft = '5px';
                    deleteButton.style.cursor = 'pointer';
                    deleteButton.style.fontSize = '15px';
                    deleteButton.classList.add('delete-file-button');
                    deleteButton.setAttribute('data-filename', newFiles[i].name);
                    deleteButton.onclick = function () {
                        const filenameToRemove = this.getAttribute('data-filename');
                        const dataTransfer = new DataTransfer();
                        const files = savedInput.files;
                        for (let i = 0; i < files.length; i++) {
                            if (files[i].name !== filenameToRemove) {
                                dataTransfer.items.add(files[i]);
                            }
                        }
                        savedInput.files = dataTransfer.files;
                        savedInput.dispatchEvent(changeEvent);
                        listItem.remove();
                    };
                    listItem.appendChild(deleteButton);
                    fileNameDisplay.appendChild(listItem);
                }
                this.value = '';
            });
            savedInput.addEventListener('change', function () {
                document.querySelector('.form-sale-order-confirm').style.display = this.files.length > 0 ? 'block' : 'none';
            });
        }

        if (duplicateQtyData) {
            duplicateQtyData.addEventListener("input", function () {
                const submitButton = document.querySelector('.duplicate-submit-button');
                if (this.valueAsNumber >= 0) {
                    submitButton.style.display = 'block';
                } else {
                    submitButton.style.display = 'none';
                }
            })
        }

        if (addToCart) {
            addToCart.addEventListener("click", function () {
                const inputQty = document.querySelector('input[id="batches_count"]'),
                    batchesSpan = document.querySelector("span[data-batches-count]"),
                    batch = batchesSpan?.dataset.batchesCount;
                if (this.classList.contains('not-confirmed-order')) {
                    if (inputQty && batch && parseFloat(inputQty.value) === 0) {
                        return false;
                    }
                    const confirmOrderButton = document.getElementById('confirm_order_form');
                    confirmOrderButton.style.display = 'block';
                }
            })
        }
    });
});
