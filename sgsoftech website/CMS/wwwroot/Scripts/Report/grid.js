const gridOptions = {
    columnDefs: [],
    defaultColDef: {
        //flex: 1, //for autosize column
        editable: false,
        sortable: true,
        filter: true,
        floatingFilter: true,
        resizable: true
    },
    rowData: [],
    //pagination: true,
    //paginationPageSize: 15,
    cacheQuickFilter: true
};
let floatingFiltersHeight = 0;
function getParams() {
    return {
        prependContent: getValue('#prependContent'),
        appendContent: getValue('#appendContent'),
        suppressQuotes: undefined,
        columnSeparator: undefined,
    };
}

function onBtnView() {
    gridOptions.api.setColumnDefs([]);
    gridOptions.api.setRowData([]);
    const reportType = document.getElementById('SelectReportType').value;
    const fromDate = document.getElementById('FromDate').value;
    const toDate = document.getElementById('ToDate').value;
    const dateRegEx = /^\d{4}[./-]\d{2}[./-]\d{2}T\d{2}:\d{2}:\d{2}$/;
    const datetimeRegEx = /^\d{4}[./-]\d{2}[./-]\d{2}T\d{2}:\d{2}:\d{2}.\d{2,}$/;
    agGrid.simpleHttpRequest({
        url: '/Report/GetReportData?reportType=' + reportType + '&fromDate=' + fromDate + '&toDate=' + toDate
    }).then((data) => {
        if (data == null || data.length == 0) return;
        const columns = Object.keys(data[0]);
        const colDefs = gridOptions.api.getColumnDefs();
        colDefs.length = 0;
        columns.forEach(column => {
            if (data[0][column] != null && data[0][column].toString().match(dateRegEx) != null) {
                colDefs.push({ field: column, valueFormatter: dateFormatter });
            }
            else if (data[0][column] != null && data[0][column].toString().match(datetimeRegEx) != null) {
                colDefs.push({ field: column, valueFormatter: datetimeFormatter });
            }
            else {
                if (column != 'userId') {
                    colDefs.push({ field: column});
                }
            }

        });
        gridOptions.api.setColumnDefs(colDefs);
        gridOptions.api.setRowData(data);
        $('.ag-header-cell-menu-button').remove();
    });
}

function padTo2Digits(num) {
    return num.toString().padStart(2, '0');
}

function dateFormatter(params) {
    const date = new Date(params.value);
    if (date.getFullYear() == 1) return '';
    return [
        padTo2Digits(date.getDate()),
        padTo2Digits(date.getMonth() + 1),
        date.getFullYear(),
    ].join('/');
}

function datetimeFormatter(params) {
    const date = new Date(params.value);
    if (date.getFullYear() == 1) return '';
    const dateStr = [
        padTo2Digits(date.getDate()),
        padTo2Digits(date.getMonth() + 1),
        date.getFullYear()
    ].join('/');
    const timeStr = [
        padTo2Digits(date.getHours()),
        padTo2Digits(date.getMinutes()),
        padTo2Digits(date.getSeconds())
    ].join(':');

    return [dateStr, timeStr].join(' ');
}
function onBtnPrint() {
    setControlsDisplay(true);

    setTimeout(function () {
        print();
        setControlsDisplay(false);
    }, 2000);
}

function setControlsDisplay(isPrinterFriendly) {
    const eGridDiv = document.getElementById('reportGrid');
    const btnExport = document.getElementById('btnExport');
    const btnPrint = document.getElementById('btnPrint');
    const btnView = document.getElementById('btnView');
    const filterTextBox = document.getElementById('filter-text-box');
    const pageFooter = document.getElementsByClassName('footer')[0];
    if (isPrinterFriendly) {
        eGridDiv.style.height = '';
        btnExport.style.display = 'none';
        btnPrint.style.display = 'none';
        btnView.style.display = 'none';
        filterTextBox.style.display = 'none';
        pageFooter.style.display = 'none';
        //gridOptions.api.sizeColumnsToFit();
        floatingFiltersHeight = parseFloat(document.getElementsByClassName('ag-header-viewport')[0].getElementsByClassName('ag-header-row ag-header-row-column-filter')[0]?.style?.height);
        gridOptions.api.setFloatingFiltersHeight(0);
        $('.ag-header-cell-menu-button').remove();
        gridOptions.api.setDomLayout('print');
    }
    else {
        eGridDiv.style.height = '700px';
        btnExport.style.display = '';
        btnPrint.style.display = '';
        btnView.style.display = '';
        filterTextBox.style.display = '';
        pageFooter.style.display = '';
        floatingFiltersHeight = isNaN(floatingFiltersHeight) || 0 ? 48 : floatingFiltersHeight;
        gridOptions.api.setFloatingFiltersHeight(floatingFiltersHeight);
        gridOptions.api.setDomLayout();
    }
}

function onBtnExport() {
    const params = getParams();
    gridOptions.api.exportDataAsCsv(params);
}

function onFilterTextBoxChanged() {
    gridOptions.api.setQuickFilter(
        document.getElementById('filter-text-box').value
    );
}

function getValue(inputSelector) {
    const text = document.querySelector(inputSelector)?.value;
    switch (text) {
        case 'string':
            return (
                'Here is a comma, and a some "quotes". You can see them using the\n' +
                'api.getDataAsCsv() button but they will not be visible when the downloaded\n' +
                'CSV file is opened in Excel because string content passed to\n' +
                'prependContent and appendContent is not escaped.'
            );
        case 'array':
            return [
                [],
                [
                    {
                        data: {
                            value: 'Here is a comma, and a some "quotes".',
                            type: 'String',
                        },
                    },
                ],
                [
                    {
                        data: {
                            value:
                                'They are visible when the downloaded CSV file is opened in Excel because custom content is properly escaped (provided that suppressQuotes is not set to true)',
                            type: 'String',
                        },
                    },
                ],
                [
                    { data: { value: 'this cell:', type: 'String' }, mergeAcross: 1 },
                    {
                        data: {
                            value: 'is empty because the first cell has mergeAcross=1',
                            type: 'String',
                        },
                    },
                ],
                [],
            ];
        case 'none':
            return;
        default:
            return text;
    }
}

// wait for the document to be loaded, otherwise
// AG Grid will not find the div in the document.
document.addEventListener('DOMContentLoaded', function () {
    const eGridDiv = document.querySelector('#reportGrid');
    agGrid.Grid(eGridDiv, gridOptions);
});