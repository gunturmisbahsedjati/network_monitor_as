// Variabel Global untuk Timer
let intervalId = null
let isScanning = false

document.addEventListener('DOMContentLoaded', function () {
    // Jalankan cek pertama kali
    checkAllHosts()

    // Event Listener untuk Switch Auto Refresh
    document.getElementById('autoRefreshSwitch').addEventListener('change', function () {
        toggleAutoRefresh(this.checked)
    })

    // Event Listener jika Interval diubah saat sedang jalan
    document.getElementById('refreshInterval').addEventListener('change', function () {
        const isChecked = document.getElementById('autoRefreshSwitch').checked
        if (isChecked) {
            // Restart timer dengan interval baru
            toggleAutoRefresh(false)
            toggleAutoRefresh(true)
        }
    })
})

function toggleAutoRefresh(enable) {
    const statusText = document.getElementById('statusText')
    const liveIndicator = document.getElementById('liveIndicator')
    const btnManual = document.getElementById('btnManualRefresh')
    const intervalMs = parseInt(document.getElementById('refreshInterval').value)

    if (enable) {
        // Mode ON
        statusText.textContent = 'Live Monitoring Active'
        statusText.classList.add('text-danger', 'fw-bold')
        statusText.classList.remove('text-white')
        liveIndicator.style.display = 'inline-block'
        btnManual.disabled = true

        // Jalankan interval
        intervalId = setInterval(() => {
            // Hanya jalankan jika scan sebelumnya sudah selesai
            if (!isScanning) {
                checkAllHosts()
            }
        }, intervalMs)
    } else {
        // Mode OFF
        statusText.textContent = 'Ready'
        statusText.classList.remove('text-danger', 'fw-bold')
        statusText.classList.add('text-white')
        liveIndicator.style.display = 'none'
        btnManual.disabled = false

        clearInterval(intervalId)
    }
}

function manualCheck() {
    if (!isScanning) checkAllHosts()
}

function checkAllHosts() {
    const rows = document.querySelectorAll('.host-row')
    if (rows.length === 0) return

    isScanning = true
    document.getElementById('progressBar').style.width = '10%'

    let completedRequests = 0
    const totalRequests = rows.length

    // Update UI jadi spinner (hanya jika bukan mode realtime yg cepat, opsional)
    // Di mode realtime, lebih baik badge tidak berubah jadi spinner semua sekaligus agar tidak pusing
    // Kita biarkan user melihat update badge secara langsung.

    rows.forEach((row) => {
        const id = row.getAttribute('data-id')
        const ip = row.getAttribute('data-ip')
        const statusCell = row.querySelector('.status-cell')
        const timeCell = row.querySelector('.last-checked-cell')

        // Visual cue kecil bahwa sedang diproses (opsional)
        // statusCell.style.opacity = "0.5";

        fetch('/api/ping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, ip: ip })
        })
            .then((response) => response.json())
            .then((data) => {
                //timeCell.textContent = data.last_checked.split(' ')[1] // Ambil jam saja biar singkat
                timeCell.textContent = data.last_checked // Ambil jam saja biar singkat

                if (data.status === 'up') {
                    statusCell.innerHTML = '<span class="badge bg-success rounded-pill status-badge" data-status="up"><i class="bi bi-check-circle-fill me-1"></i>ONLINE</span>'
                } else {
                    statusCell.innerHTML = '<span class="badge bg-danger rounded-pill status-badge" data-status="down"><i class="bi bi-x-circle-fill me-1"></i>OFFLINE</span>'
                }
            })
            .catch((error) => {
                console.error(error)
            })
            .finally(() => {
                completedRequests++
                // Update Progress Bar
                const percent = (completedRequests / totalRequests) * 100
                document.getElementById('progressBar').style.width = percent + '%'

                if (completedRequests === totalRequests) {
                    isScanning = false
                    updateStatsUI()
                    // Reset progress bar setelah sebentar
                    setTimeout(() => {
                        document.getElementById('progressBar').style.width = '0%'
                    }, 500)
                }
            })
    })
}

function updateStatsUI() {
    const badges = document.querySelectorAll('.status-badge')
    let online = 0
    let offline = 0
    badges.forEach((badge) => {
        if (badge.getAttribute('data-status') === 'up') online++
        if (badge.getAttribute('data-status') === 'down') offline++
    })
    document.getElementById('online-count').textContent = online
    document.getElementById('offline-count').textContent = offline
}

// --- FUNGSI CRUD ---

// 1. Tambah Device Baru
function saveNewDevice() {
    const name = document.getElementById('addName').value
    const ip = document.getElementById('addIP').value

    if (!name || !ip) {
        alert('Mohon isi semua data')
        return
    }

    fetch('/api/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, ip: ip })
    })
        .then((res) => res.json())
        .then((data) => {
            if (data.success) {
                location.reload() // Refresh halaman agar tabel terupdate
            } else {
                alert('Gagal menambah: ' + data.error)
            }
        })
}

// 2. Buka Modal Edit
function openEditModal(id, name, ip) {
    document.getElementById('editId').value = id
    document.getElementById('editName').value = name
    document.getElementById('editIP').value = ip
    new bootstrap.Modal(document.getElementById('editModal')).show()
}

// 3. Simpan Perubahan Edit
function updateDevice() {
    const id = document.getElementById('editId').value
    const name = document.getElementById('editName').value
    const ip = document.getElementById('editIP').value

    fetch('/api/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, name: name, ip: ip })
    })
        .then((res) => res.json())
        .then((data) => {
            if (data.success) {
                location.reload()
            } else {
                alert('Gagal update: ' + data.error)
            }
        })
}

// 4. Buka Modal Hapus
function openDeleteModal(id, name) {
    document.getElementById('deleteId').value = id
    document.getElementById('deleteNameDisplay').innerText = name
    new bootstrap.Modal(document.getElementById('deleteModal')).show()
}

// 5. Konfirmasi Hapus
function confirmDelete() {
    const id = document.getElementById('deleteId').value
    fetch('/api/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id })
    })
        .then((res) => res.json())
        .then((data) => {
            if (data.success) {
                location.reload()
            } else {
                alert('Gagal menghapus: ' + data.error)
            }
        })
}

// Variable global untuk modal
let chatModal

document.addEventListener('DOMContentLoaded', function () {
    chatModal = new bootstrap.Modal(document.getElementById('aiModal'))
})

// Fungsi membuka Chat
function openChat() {
    chatModal.show()
    // Opsional: Otomatis sapa user pertama kali
    const container = document.getElementById('chatContainer')
    if (container.children.length <= 1) {
        // Jika masih kosong (cuma placeholder)
        // Kita bisa trigger pesan otomatis "Halo" dari AI jika mau, atau biarkan kosong
    }
}

// Handle tombol Enter
function handleEnter(e) {
    if (e.key === 'Enter') sendMessage()
}

// Fungsi Mengirim Pesan
function sendMessage() {
    const inputField = document.getElementById('userInput')
    const message = inputField.value.trim()
    if (!message) return

    // 1. Tampilkan Pesan User di UI
    addBubble(message, 'user')
    inputField.value = ''

    // Hapus placeholder jika ada
    const placeholder = document.getElementById('chatPlaceholder')
    if (placeholder) placeholder.remove()

    // 2. Tampilkan Loading Bubble
    const loadingId = addLoadingBubble()

    // 3. Kirim ke Backend
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    })
        .then((response) => response.json())
        .then((data) => {
            // Hapus loading
            removeBubble(loadingId)

            if (data.success) {
                // Tampilkan Balasan AI
                // Kita convert newline (\n) jadi <br> agar rapi
                let formattedText = data.reply.replace(/\n/g, '<br>')
                // Ubah **teks** menjadi bold (simple markdown)
                formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')

                addBubble(formattedText, 'ai')
            } else {
                addBubble('Maaf, terjadi error: ' + data.error, 'ai')
            }
        })
        .catch((err) => {
            removeBubble(loadingId)
            addBubble('Gagal terhubung ke server.', 'ai')
        })
}

// Helper: Menambah Bubble ke UI
function addBubble(text, sender) {
    const container = document.getElementById('chatContainer')
    const div = document.createElement('div')
    div.classList.add('chat-bubble')
    div.classList.add(sender === 'user' ? 'user-msg' : 'ai-msg')
    div.innerHTML = text // Gunakan innerHTML agar support <b> dan <br>
    container.appendChild(div)

    // Auto scroll ke bawah
    container.scrollTop = container.scrollHeight
    return div.id // Return ID kalau butuh dihapus
}

// Helper: Bubble Loading Animasi
function addLoadingBubble() {
    const id = 'loading-' + Date.now()
    const container = document.getElementById('chatContainer')
    const div = document.createElement('div')
    div.id = id
    div.classList.add('chat-bubble', 'ai-msg')
    div.innerHTML = '<div class="spinner-grow spinner-grow-sm" role="status"></div> Mengetik...'
    container.appendChild(div)
    container.scrollTop = container.scrollHeight
    return id
}

function removeBubble(id) {
    const el = document.getElementById(id)
    if (el) el.remove()
}

// Fungsi membuka Modal dan Load Data
function openHistory() {
    const modal = new bootstrap.Modal(document.getElementById('historyModal'));
    modal.show();
    loadHistoryData();
}

// Fungsi Fetch Data dari API
function loadHistoryData() {
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center">Memuat data...</td></tr>';

    fetch('/api/history')
        .then(res => res.json())
        .then(data => {
            tbody.innerHTML = ''; // Kosongkan loading

            if (data.success && data.logs.length > 0) {
                data.logs.forEach(log => {
                    // Tentukan warna badge
                    let badgeClass = log.status === 'UP' ? 'bg-success' : 'bg-danger';
                    let icon = log.status === 'UP' ? 'bi-arrow-up-circle' : 'bi-arrow-down-circle';
                    let text = log.status === 'UP' ? 'PERANGKAT UP' : 'PERANGKAT DOWN';

                    const row = `
                    <tr>
                        <td class="small">${log.event_time}</td>
                        <td class="fw-bold">${log.name}</td>
                        <td class="text-muted small">${log.ip_address}</td>
                        <td class="text-center">
                            <span class="badge ${badgeClass}">
                                <i class="bi ${icon}"></i> ${text}
                            </span>
                        </td>
                    </tr>
                `;
                    tbody.innerHTML += row;
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Belum ada riwayat kejadian.</td></tr>';
            }
        })
        .catch(err => {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Gagal memuat data.</td></tr>';
        });
}