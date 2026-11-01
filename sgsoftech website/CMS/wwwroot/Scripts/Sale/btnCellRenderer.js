class BtnCellRenderer {
    init(params) {
        this.params = params;

        this.eGui = document.createElement('button');
        //this.eGui.innerHTML = 'Remove';
        this.eGui.type = 'button';
        this.eGui.className = 'btn-sm btn-danger fa-solid fa-trash-can';
        this.btnClickedHandler = this.btnClickedHandler.bind(this);
        this.eGui.addEventListener('click', this.btnClickedHandler);
    }

    getGui () {
        return this.eGui;
    }

    destroy () {
        this.eGui.removeEventListener('click', this.btnClickedHandler);
    }

    btnClickedHandler (event) {
        this.params.clicked(this.params.node);
    }
}