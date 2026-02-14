// =========================================
// Excel to JSON Converter Modal
// =========================================

let excelJsonFileName = '';

function convertExcelToJson() {
    // Open the modal
    const modal = document.getElementById('excelConverterModal');
    modal.style.display = 'flex';
    
    // Add click handler to close modal when clicking outside
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeExcelConverterModal();
        }
    };
    
    // Reset the modal state
    resetExcelModal();
}

function closeExcelConverterModal() {
    const modal = document.getElementById('excelConverterModal');
    modal.style.display = 'none';
    modal.onclick = null; // Remove click handler
    resetExcelModal();
}

function resetExcelModal() {
    document.getElementById('excelModalFileInput').value = '';
    document.getElementById('excelModalFileLabel').classList.remove('selected');
    document.getElementById('excelModalFileLabel').innerHTML = `
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <p>Click to select Excel file</p>
        <span>Supports .xlsx and .xls</span>
    `;
    document.getElementById('modalConvertBtn').disabled = true;
    document.getElementById('modalConvertBtn').textContent = 'Convert to JSON';
    document.getElementById('modalDownloadBtn').style.display = 'none';
    document.getElementById('modalStatus').className = 'modal-status';
    document.getElementById('modalStatus').style.display = 'none';
    excelJsonFileName = '';
}

function handleExcelFileSelect(input) {
    const label = document.getElementById('excelModalFileLabel');
    const convertBtn = document.getElementById('modalConvertBtn');
    const statusEl = document.getElementById('modalStatus');
    
    statusEl.style.display = 'none';
    
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const fileName = file.name;
        const fileExt = fileName.split('.').pop().toLowerCase();
        
        if (fileExt === 'xlsx' || fileExt === 'xls') {
            label.classList.add('selected');
            label.innerHTML = `
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #4CAF50;">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
                <p style="color: #4CAF50; font-weight: 500;">${fileName}</p>
                <span style="color: #999;">Ready to convert</span>
            `;
            convertBtn.disabled = false;
        } else {
            showModalStatus('Please select a valid Excel file (.xlsx or .xls)', 'error');
            input.value = '';
            convertBtn.disabled = true;
        }
    } else {
        label.classList.remove('selected');
        label.innerHTML = `
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <p>Click to select Excel file</p>
            <span>Supports .xlsx and .xls</span>
        `;
        convertBtn.disabled = true;
    }
}

function convertExcelModal() {
    const fileInput = document.getElementById('excelModalFileInput');
    const convertBtn = document.getElementById('modalConvertBtn');
    const downloadBtn = document.getElementById('modalDownloadBtn');
    
    if (!fileInput.files[0]) {
        showModalStatus('Please select a file first', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    convertBtn.disabled = true;
    convertBtn.innerHTML = '<span class="spin"></span> Converting...';
    
    showModalStatus('Converting your Excel file to JSON...', 'info');
    
    fetch('/convert', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            excelJsonFileName = data.json_file;
            downloadBtn.style.display = 'flex';
            convertBtn.innerHTML = '✓ Converted!';
            convertBtn.style.background = '#4CAF50';
            showModalStatus('Conversion successful! Click "Download JSON" to save the file.', 'success');
        } else {
            convertBtn.disabled = false;
            convertBtn.textContent = 'Convert to JSON';
            showModalStatus('Conversion failed: ' + data.message, 'error');
        }
    })
    .catch(error => {
        convertBtn.disabled = false;
        convertBtn.textContent = 'Convert to JSON';
        showModalStatus('Error: ' + error.message, 'error');
    });
}

function downloadExcelJson() {
    if (excelJsonFileName) {
        // Trigger download
        window.location.href = '/download/' + excelJsonFileName;
        
        // Close modal after a short delay to allow download to start
        setTimeout(() => {
            closeExcelConverterModal();
        }, 500);
    }
}

function showModalStatus(message, type) {
    const statusEl = document.getElementById('modalStatus');
    statusEl.textContent = message;
    statusEl.className = 'modal-status ' + type;
}
