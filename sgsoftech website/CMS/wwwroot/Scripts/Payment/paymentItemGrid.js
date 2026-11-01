const gridOptions = {
    columnDefs: [
        { headerName: 'SaleId', field: 'saleId', editable: false, minWidth: columnWidth(15), maxWidth: 75 },
        { headerName: 'Amount', field: 'totalAmount', minWidth: columnWidth(15),editable: false },
        { headerName: 'Paid', field: 'amount', minWidth: columnWidth(15), cellEditor: NumericCellEditor },
        { headerName: 'Total Paid', field: 'totalPaidAmount', minWidth: columnWidth(18), editable: false },
        { headerName: 'Balance', field: 'balanceAmount', minWidth: columnWidth(18), editable: false },
        { headerName: 'Description', field: 'description', minWidth: columnWidth(20),},

    ],
    defaultColDef: {
        flex: 1,
        editable: true,
    },
    
    rowData: [],
    rowSelection: 'single',
    suppressDragLeaveHidesColumns: true,
    animateRows: true,
    editType: 'fullRow',
    //onCellValueChanged: onCellValueChanged,
    //onRowValueChanged: onRowValueChanged,
};

function onCellValueChanged(event) {
    if (event.column.colId === "amount" && event.oldValue != event.newValue) {
        const amount = document.getElementById('TotalAmount').value;
        allocatePaidAmount(amount, event.node.rowIndex);
        calulateBalanceAmount();
    }

}

//function onRowValueChanged(event) {
//    var data = event.data;
//}

function getGridData() {
    gridOptions.api.stopEditing();
    let paymentGridItems = [];
    gridOptions.api.forEachNode((rowNode, index) => {
        if (rowNode.data.amount > 0) {
            paymentGridItems.push(rowNode.data);
        }
    });

    document.getElementById('PaymentItemJson').value = encodeURIComponent(JSON.stringify(paymentGridItems));
}

function allocatePaidAmount(amount, rIndex) {
    gridOptions.api.removeEventListener('cellValueChanged', onCellValueChanged);
    let totalAllocatedAmt = calulateTotalAllocated();
    amount = Number(amount) - totalAllocatedAmt;
    amount = amount > 0 ? amount : 0;
    gridOptions.api.forEachNode((rowNode, index) => {
        if ((rIndex == null || rowNode.rowIndex > rIndex) && Number(rowNode.data.amount) == 0) {
            const paidAmt = Number(rowNode.data.totalAmount) - Number(rowNode.data.totalPaidAmount);
            if (amount >= paidAmt && paidAmt > 0) {
                rowNode.setDataValue('amount', paidAmt);
            }
            else if (paidAmt > 0) {
                rowNode.setDataValue('amount', amount);
            }
            const reducingTotalAmount = amount - Number(rowNode.data.amount);
            amount = reducingTotalAmount > 0 ? reducingTotalAmount : 0;
        }
    });

    gridOptions.api.forEachNode((rowNode, index) => {
        if (rowNode.rowIndex < rIndex && Number(rowNode.data.amount) == 0) {
            const paidAmt = Number(rowNode.data.totalAmount) - Number(rowNode.data.totalPaidAmount);
            if (amount >= paidAmt && paidAmt > 0) {
                rowNode.setDataValue('amount', paidAmt);
            }
            else if (paidAmt > 0) {
                rowNode.setDataValue('amount', amount);
            }
            const reducingTotalAmount = amount - Number(rowNode.data.amount);
            amount = reducingTotalAmount > 0 ? reducingTotalAmount : 0;
        }

    });

    gridOptions.api.addEventListener('cellValueChanged', onCellValueChanged);
}

function calulateBalanceAmount() {
    gridOptions.api.forEachNode((rowNode, index) => {
        rowNode.setDataValue('balanceAmount', rowNode.data.totalAmount - Number(rowNode.data.amount) - rowNode.data.totalPaidAmount);
    });
}

function calulateTotalAllocated() {
    let totalPaid = Number(0);
    gridOptions.api.forEachNode((rowNode, index) => {
        totalPaid += Number(rowNode.data.amount);
    });
    return totalPaid;
}

function getAccountGridData(accountFromId, accountToId) {
    agGrid.simpleHttpRequest({
        url: '/Payment/GetPaymentItems?accountFromId=' + accountFromId + '&accountToId=' + accountToId
    }).then((data) => {
        gridOptions.api.setRowData(data);
        const totalAmount = document.getElementById('TotalAmount').value;
        allocatePaidAmount(totalAmount);
        calulateBalanceAmount();
    })
}
function columnWidth(percentage) {
    const parent = $("#paymentItemGrid").parent();
    const width = parent.width() * percentage / 100;  // Pixel calculation
    return width;
}