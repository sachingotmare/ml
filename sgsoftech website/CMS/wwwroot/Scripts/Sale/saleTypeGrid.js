var serviceData = [];

const gridOptions = {
    columnDefs: [
        {
            headerName: 'Service',
            field: 'serviceTitle',
            minWidth: columnWidth(25),
            cellEditor: 'agSelectCellEditor',
            cellEditorParams: {
                values: [],
            }
        },
        {
            headerName: 'Quantity', field: 'quantity',
            maxWidth: 115,
            minWidth: columnWidth(18),
            cellEditor: NumericCellEditor
        },
        { field: 'rate', cellEditor: NumericCellEditor, minWidth: columnWidth(18),editable: false },
        {
            headerName: 'Amount', field: 'amount', minWidth: columnWidth(18),
            cellEditor: NumericCellEditor
        },
        {
            //headerGroupComponent: CustomHeaderGroup,
            editable: false,
            minWidth: columnWidth(20),
            maxWidth: 70,
            headerName: '',
            cellRenderer: BtnCellRenderer,
            cellRendererParams: {
                clicked: function (node) {
                    //const selectedRows = gridOptions.api.getSelectedRows();
                    gridOptions.api.applyTransaction({ remove: [node.data] }); // remove row from grid
                    calculateTotalAmount();
                }
            },
            headerComponentParams: {
                template:
                    '<div class="ag-cell-label-container" role="presentation">' +
                    '  <span ref="eMenu" class="ag-header-icon ag-header-cell-menu-button"></span>' +
                    '  <div ref="eLabel" class="ag-header-cell-label" role="presentation">' +
                    '    <span ref="eSortOrder" class="ag-header-icon ag-sort-order" ></span>' +
                    '    <span ref="eSortAsc" class="ag-header-icon ag-sort-ascending-icon" ></span>' +
                    '    <span ref="eSortDesc" class="ag-header-icon ag-sort-descending-icon" ></span>' +
                    '    <span ref="eSortNone" class="ag-header-icon ag-sort-none-icon" ></span>' +
                    //The line below is the key for achieving the solution
                    '    <button type="button" id="newServiceEntry" class = "btn-sm btn-info fa-solid fa-circle-plus" onClick = "onAddNewRowClick()"> <span ref="eText" class="ag-header-cell-text" role="columnheader"></span></button>' +
                    '    <span ref="eFilter" class="ag-header-icon ag-filter-icon"></span>' +
                    '  </div>' +
                    '</div>'
            },
        }
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
    onCellValueChanged: onCellValueChanged,
};

function onAddNewRowClick() {
    gridOptions.api.applyTransaction({ add: [{}] }); // add new row in grid
    const lastRowIndex = gridOptions.api.getLastDisplayedRow()
    gridOptions.api.startEditingCell({
        rowIndex: lastRowIndex,
        colKey: 'serviceTitle',
    });
}

function onCellValueChanged(event) {
    if (event.column.colId === "serviceTitle") {
        const si = serviceData.find(p => p.title === event.value);
        event.node.setDataValue('rate', si.rate);
        if (si.quantity > 0) {
            event.node.setDataValue('Quantity', si.quantity);
        }
        
    }
    if (event.column.colId !== "amount") {
        if (event.node.data.quantity > 0) {
            event.node.setDataValue('amount', event.node.data.quantity * event.node.data.rate);
        }
        else {
            event.node.setDataValue('amount', event.node.data.rate);
        }
    }
    
    calculateTotalAmount();
}

function calculateTotalAmount() {
    let totalAmount = 0;
    gridOptions.api.forEachNode((rowNode, index) => {
        totalAmount += parseInt(rowNode.data.amount);
    });

    document.getElementById('TotalAmount').value = totalAmount;
}

function getItemGridData() {
    gridOptions.api.stopEditing();
    let saleItems = [];
    gridOptions.api.forEachNode((rowNode, index) => {
        const si = serviceData.find(p => p.title === rowNode.data.serviceTitle);
        rowNode.data.ServiceId = si.id;
       
       saleItems.push(rowNode.data);
    });

    document.getElementById('SaleItemsJson').value = encodeURIComponent(JSON.stringify(saleItems));
}

function columnWidth(percentage) {
    const width = $("#saleTypeGrid").parent().width() * percentage / 100;  // Pixel calculation
    return width;
}