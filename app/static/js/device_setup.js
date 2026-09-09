// Device Setup - JavaScript
// PIENG Energy Meter - Sistema Universal de Cadastro

let currentEngine = null;
let clients = [];

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    loadClients();
    loadDevices();
});

// ============================================================================
// ENGINE SELECTION
// ============================================================================

function selectEngine(engine) {
    currentEngine = engine;
    
    // Hide selection grid
    document.getElementById('engines-selection').style.display = 'none';
    
    // Show selected form
    const formId = `form-${engine}`;
    const formElement = document.getElementById(formId);
    if (formElement) {
        formElement.classList.add('active');
    }
    
    // Pre-fill client name if available
    if (clients.length > 0) {
        const clientNameField = document.getElementById(`${engine}_client_name`);
        if (clientNameField) {
            clientNameField.value = clients[0].name;
        }
    }
}

function backToSelection() {
    currentEngine = null;
    
    // Show selection grid
    document.getElementById('engines-selection').style.display = 'block';
    
    // Hide all forms
    const forms = document.querySelectorAll('.form-container');
    forms.forEach(form => {
        form.classList.remove('active');
    });
    
    // Hide alert
    hideAlert();
}

// ============================================================================
// GENERIC FORM FIELDS TOGGLE
// ============================================================================

function toggleGenericFields() {
    const connectionType = document.getElementById('generic_connection_type').value;
    const tcpFields = document.getElementById('generic_tcp_fields');
    const serialFields = document.getElementById('generic_serial_fields');
    
    if (connectionType === 'tcp') {
        tcpFields.style.display = 'block';
        serialFields.style.display = 'none';
    } else {
        tcpFields.style.display = 'none';
        serialFields.style.display = 'block';
    }
}

// ============================================================================
// LOAD CLIENTS
// ============================================================================

async function loadClients() {
    try {
        const response = await fetch('/api/clients');
        if (response.ok) {
            clients = await response.json();
        }
    } catch (error) {
        console.error('Error loading clients:', error);
    }
}

// ============================================================================
// LOAD DEVICES
// ============================================================================

async function loadDevices() {
    try {
        const response = await fetch('/api/devices');
        if (response.ok) {
            const devices = await response.json();
            displayDevices(devices);
        }
    } catch (error) {
        console.error('Error loading devices:', error);
        document.getElementById('devices-container').innerHTML = 
            '<p style="color: #dc3545; text-align: center; padding: 20px;">Erro ao carregar dispositivos</p>';
    }
}

function displayDevices(devices) {
    const container = document.getElementById('devices-container');
    
    if (devices.length === 0) {
        container.innerHTML = '<p style="color: var(--text-faint); text-align: center; padding: 20px;">Nenhum dispositivo cadastrado ainda</p>';
        return;
    }

    const deviceTypeNames = {
        'tuya': 'Tuya Cloud',
        'modbus': 'Modbus RTU',
        'modbus_tcp': 'Modbus TCP'
    };

    container.innerHTML = devices.map(device => `
        <div class="device-item">
            <div class="device-info">
                <div class="device-name">${device.name}</div>
                <div class="device-type">${deviceTypeNames[device.device_type] || device.device_type} · ${deviceIdentifier(device)}</div>
            </div>
            <div class="device-actions">
                <span class="device-status ${device.active ? 'status-active' : 'status-inactive'}">
                    ${device.active ? 'ATIVO' : 'INATIVO'}
                </span>
                <button type="button" class="btn-icon" title="${device.active ? 'Desativar' : 'Ativar'}" onclick="toggleDeviceActive(${device.id}, ${device.active})">
                    ${device.active ? '&#10074;&#10074;' : '&#9654;'}
                </button>
                <button type="button" class="btn-icon btn-icon-danger" title="Apagar dispositivo" onclick="deleteDevice(${device.id}, '${device.name.replace(/'/g, "\\'")}')">
                    &#10005;
                </button>
            </div>
        </div>
    `).join('');
}

function deviceIdentifier(device) {
    const cfg = device.config || {};
    if (cfg.device_id) return cfg.device_id;
    if (cfg.host) return `${cfg.host}:${cfg.port || ''}`;
    if (cfg.port) return `${cfg.port} (slave ${cfg.slave_id ?? '?'})`;
    return `id ${device.id}`;
}

// ============================================================================
// DELETE / TOGGLE DEVICE
// ============================================================================

async function deleteDevice(deviceId, deviceName) {
    const confirmed = confirm(`Apagar o dispositivo "${deviceName}"?\n\nIsso remove o cadastro e TODO o histórico de medições dele. Essa ação não pode ser desfeita.`);
    if (!confirmed) return;

    try {
        const response = await fetch(`/api/devices/${deviceId}`, { method: 'DELETE' });
        const result = await response.json();

        if (response.ok && result.success) {
            showAlert(`Dispositivo "${deviceName}" apagado`, 'success');
            loadDevices();
        } else {
            showAlert('Erro ao apagar dispositivo', 'error');
        }
    } catch (error) {
        console.error('Error deleting device:', error);
        showAlert(`Erro: ${error.message}`, 'error');
    }
}

async function toggleDeviceActive(deviceId, currentActive) {
    try {
        const response = await fetch(`/api/devices/${deviceId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active: !currentActive })
        });

        if (response.ok) {
            loadDevices();
        } else {
            showAlert('Erro ao atualizar dispositivo', 'error');
        }
    } catch (error) {
        console.error('Error toggling device:', error);
        showAlert(`Erro: ${error.message}`, 'error');
    }
}

// ============================================================================
// FORM SUBMISSION
// ============================================================================

async function submitForm(event, engineType) {
    event.preventDefault();
    
    try {
        // Get form data based on engine type
        const formData = getFormData(engineType);
        
        if (!formData) {
            showAlert('Erro ao coletar dados do formulário', 'error');
            return;
        }
        
        // Create or get client
        const clientId = await ensureClient(formData.clientName);
        
        if (!clientId) {
            showAlert('Erro ao criar/buscar cliente', 'error');
            return;
        }
        
        // Create device
        const device = await createDevice(clientId, formData);
        
        if (device) {
            showAlert('Dispositivo cadastrado com sucesso! O poller vai começar a coletar dados em até 30 segundos.', 'success');

            // Reload devices list
            setTimeout(() => {
                loadDevices();
                backToSelection();
            }, 2000);
        } else {
            showAlert('Erro ao cadastrar dispositivo', 'error');
        }
        
    } catch (error) {
        console.error('Error submitting form:', error);
        showAlert(`Erro: ${error.message}`, 'error');
    }
}

// ============================================================================
// GET FORM DATA
// ============================================================================

function getFormData(engineType) {
    const getValue = (id) => {
        const element = document.getElementById(id);
        return element ? element.value : null;
    };
    
    const getNumberValue = (id) => {
        const value = getValue(id);
        return value ? parseFloat(value) : null;
    };
    
    let formData = null;
    
    switch (engineType) {
        case 'tuya':
            formData = {
                clientName: getValue('tuya_client_name'),
                deviceName: getValue('tuya_device_name'),
                deviceType: 'tuya',
                config: {
                    device_id: getValue('tuya_device_id'),
                    metrics: ['energy', 'voltage', 'current', 'power']
                }
            };
            break;
            
        case 'pzem_serial':
            formData = {
                clientName: getValue('pzem_serial_client_name'),
                deviceName: getValue('pzem_serial_device_name'),
                deviceType: 'modbus',
                config: {
                    port: getValue('pzem_serial_port'),
                    slave_id: getNumberValue('pzem_serial_slave_id'),
                    baudrate: getNumberValue('pzem_serial_baudrate'),
                    timeout: getNumberValue('pzem_serial_timeout'),
                    driver: 'pzem004t',
                    base: 0
                }
            };
            break;
            
        case 'pzem_tcp':
            formData = {
                clientName: getValue('pzem_tcp_client_name'),
                deviceName: getValue('pzem_tcp_device_name'),
                deviceType: 'modbus_tcp',
                config: {
                    host: getValue('pzem_tcp_host'),
                    port: getNumberValue('pzem_tcp_port'),
                    slave_id: getNumberValue('pzem_tcp_slave_id'),
                    timeout: getNumberValue('pzem_tcp_timeout'),
                    driver: 'pzem004t',
                    base: 0
                }
            };
            break;
            
        case 'sdm630_serial':
            formData = {
                clientName: getValue('sdm630_serial_client_name'),
                deviceName: getValue('sdm630_serial_device_name'),
                deviceType: 'modbus',
                config: {
                    port: getValue('sdm630_serial_port'),
                    slave_id: getNumberValue('sdm630_serial_slave_id'),
                    baudrate: getNumberValue('sdm630_serial_baudrate'),
                    timeout: getNumberValue('sdm630_serial_timeout'),
                    driver: 'sdm630',
                    base: 0
                }
            };
            break;
            
        case 'sdm630_tcp':
            formData = {
                clientName: getValue('sdm630_tcp_client_name'),
                deviceName: getValue('sdm630_tcp_device_name'),
                deviceType: 'modbus_tcp',
                config: {
                    host: getValue('sdm630_tcp_host'),
                    port: getNumberValue('sdm630_tcp_port'),
                    slave_id: getNumberValue('sdm630_tcp_slave_id'),
                    timeout: getNumberValue('sdm630_tcp_timeout'),
                    driver: 'sdm630',
                    base: 0
                }
            };
            break;
            
        case 'generic':
            const connectionType = getValue('generic_connection_type');
            
            if (connectionType === 'tcp') {
                formData = {
                    clientName: getValue('generic_client_name'),
                    deviceName: getValue('generic_device_name'),
                    deviceType: 'modbus_tcp',
                    config: {
                        host: getValue('generic_tcp_host'),
                        port: getNumberValue('generic_tcp_port'),
                        slave_id: getNumberValue('generic_slave_id'),
                        timeout: getNumberValue('generic_timeout'),
                        base: getNumberValue('generic_base'),
                        count: getNumberValue('generic_count'),
                        metrics: ['voltage', 'current', 'power', 'energy_wh']
                    }
                };
            } else {
                formData = {
                    clientName: getValue('generic_client_name'),
                    deviceName: getValue('generic_device_name'),
                    deviceType: 'modbus',
                    config: {
                        port: getValue('generic_serial_port'),
                        slave_id: getNumberValue('generic_slave_id'),
                        baudrate: getNumberValue('generic_serial_baudrate'),
                        timeout: getNumberValue('generic_timeout'),
                        base: getNumberValue('generic_base'),
                        count: getNumberValue('generic_count'),
                        metrics: ['voltage', 'current', 'power', 'energy_wh']
                    }
                };
            }
            break;
            
        default:
            console.error('Unknown engine type:', engineType);
            return null;
    }
    
    return formData;
}

// ============================================================================
// API CALLS
// ============================================================================

async function ensureClient(clientName) {
    // Check if client already exists
    const existingClient = clients.find(c => c.name === clientName);
    
    if (existingClient) {
        return existingClient.id;
    }
    
    // Create new client
    try {
        const response = await fetch('/api/clients', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: clientName,
                external_id: `CLIENT_${clientName.toUpperCase().replace(/\s+/g, '_')}`
            })
        });
        
        if (response.ok) {
            const client = await response.json();
            clients.push(client);
            return client.id;
        } else {
            const error = await response.text();
            console.error('Error creating client:', error);
            return null;
        }
    } catch (error) {
        console.error('Error creating client:', error);
        return null;
    }
}

async function createDevice(clientId, formData) {
    try {
        const response = await fetch('/api/devices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                client_id: clientId,
                name: formData.deviceName,
                device_type: formData.deviceType,
                active: true,
                config: formData.config
            })
        });
        
        if (response.ok) {
            return await response.json();
        } else {
            const error = await response.text();
            console.error('Error creating device:', error);
            showAlert(`Erro ao criar dispositivo: ${error}`, 'error');
            return null;
        }
    } catch (error) {
        console.error('Error creating device:', error);
        return null;
    }
}

// ============================================================================
// ALERT MESSAGES
// ============================================================================

function showAlert(message, type = 'success') {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = `alert alert-${type} show`;
    
    // Auto-hide after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            hideAlert();
        }, 5000);
    }
}

function hideAlert() {
    const alert = document.getElementById('alert');
    alert.classList.remove('show');
}

// ============================================================================
// UTILITIES
// ============================================================================

// Auto-refresh devices list every 30 seconds
setInterval(() => {
    if (document.getElementById('engines-selection').style.display !== 'none') {
        loadDevices();
    }
}, 30000);


