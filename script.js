// 1. LOGIKA NAVIGASI HALAMAN (SINGLE PAGE APPLICATION)
function showPage(pageId) {
    const sections = document.querySelectorAll('.page-section');
    sections.forEach(sec => {
        sec.classList.add('hidden');
        sec.classList.remove('flex'); 
    });

    const targetPage = document.getElementById('page-' + pageId);
    if (targetPage) {
        targetPage.classList.remove('hidden');
        if (pageId === 'lapor' || pageId === 'status') {
            targetPage.classList.add('flex');
        }
    }

    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => btn.classList.remove('active'));
    
    // Evaluasi tombol navigasi aktif
    const clickedBtn = Array.from(navBtns).find(btn => {
        const onClickAttr = btn.getAttribute('onclick') || '';
        return onClickAttr.includes(`'${pageId}'`);
    });
    if (clickedBtn) clickedBtn.classList.add('active');
}

// 2. INISIALISASI EVENT LISTENERS (DOM LOADED)
document.addEventListener("DOMContentLoaded", function() {
    
    // --- A. LOGIKA MODAL POP-UP MATERI ---
    const modal = document.getElementById('bullyingModal');
    const triggers = document.querySelectorAll('.trigger-modal'); 
    const closeBtn = document.getElementById('closeModalBtn');

    triggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            if (modal) {
                modal.classList.remove('hidden');
                modal.classList.add('flex');
                document.body.style.overflow = 'hidden'; // Kunci scroll background
            }
        });
    });

    if (closeBtn && modal) {
        closeBtn.addEventListener('click', function() {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.style.overflow = 'auto'; // Buka scroll background
        });
    }

    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                document.body.style.overflow = 'auto';
            }
        });
    }

    // --- B. LOGIKA FORM LAPOR SISWA (SEMBUNYIKAN IDENTITAS & PREVIEW FILE) ---
    const checkboxAnonim = document.getElementById('isAnonim');
    const dataDiri = document.getElementById('dataDiri');
    
    if (checkboxAnonim && dataDiri) {
        checkboxAnonim.addEventListener('change', function() {
            if (this.checked) {
                dataDiri.classList.add('hidden');
            } else {
                dataDiri.classList.remove('hidden');
            }
        });
    }

    const inputBukti = document.getElementById('inputBukti');
    const filePreview = document.getElementById('filePreview');

    if (inputBukti && filePreview) {
        inputBukti.addEventListener('change', function() {
            filePreview.innerHTML = ''; 
            const files = this.files;
            
            if (files.length > 0) {
                let html = `<p class="font-bold mb-1 text-gray-700">File terpilih (${files.length}):</p><ul class="list-disc ml-4 space-y-1">`;
                for (let i = 0; i < files.length; i++) {
                    const fileSizeKB = (files[i].size / 1024).toFixed(1);
                    html += `<li class="text-xs text-blue-800">${files[i].name} <span class="text-gray-500">(${fileSizeKB} KB)</span></li>`;
                }
                html += `</ul>`;
                filePreview.innerHTML = html;
            }
        });
    }

    // --- C. INTEGRASI SUBMIT FORM LAPOR (POST /api/lapor) ---
    const formLapor = document.getElementById('formLapor');
    if (formLapor) {
        formLapor.addEventListener('submit', async function(e) {
            e.preventDefault(); 
            
            const btn = document.getElementById('btnKirim');
            const originalBtnText = btn.innerHTML;
            btn.innerHTML = "Mengirim...";
            btn.disabled = true;

            const isAnonim = checkboxAnonim ? checkboxAnonim.checked : false;
            const nama = isAnonim ? "Anonim" : (document.getElementById('nama')?.value.trim() || "Anonim");
            const kelas = isAnonim ? "-" : (document.getElementById('kelas')?.value || "-");
            const cerita = document.getElementById('cerita')?.value.trim() || "";

            const checkedCategories = document.querySelectorAll('input[name="kategori"]:checked');
            if (checkedCategories.length === 0) {
                alert("Pilih minimal satu Kategori Bullying!");
                btn.innerHTML = originalBtnText;
                btn.disabled = false;
                return;
            }

            const kategori = Array.from(checkedCategories).map(cb => cb.value).join(', ');

            try {
                // Request ke Python REST API
                const response = await fetch('/api/lapor', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nama, kelas, kategori, cerita })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    formLapor.reset();
                    if (dataDiri) dataDiri.classList.remove('hidden');
                    if (filePreview) filePreview.innerHTML = '';
                    
                    const kodeTiketElem = document.getElementById('kodeTiketTampil');
                    const hasilTiketElem = document.getElementById('hasilTiket');
                    
                    if (kodeTiketElem) kodeTiketElem.innerText = result.kode_tiket;
                    if (hasilTiketElem) hasilTiketElem.classList.remove('hidden');
                } else {
                    alert("Gagal mengirim laporan: " + (result.error || "Terjadi kesalahan pada server"));
                }
            } catch (err) {
                console.error("API Request Error:", err);
                alert("Gagal terhubung ke server backend Python! Pastikan server.py telah dijalankan.");
            } finally {
                btn.innerHTML = originalBtnText;
                btn.disabled = false;
            }
        });
    }

    // --- D. INTEGRASI CEK STATUS TIKET (GET /api/cek-status) ---
    const formStatus = document.getElementById('formStatus');
    if (formStatus) {
        formStatus.addEventListener('submit', async function(e) {
            e.preventDefault();
            const inputTiket = document.getElementById('inputTiket');
            const kodeInput = inputTiket ? inputTiket.value.trim().toUpperCase() : ""; 
            const hasil = document.getElementById('hasilStatus');
            
            if (!kodeInput) {
                alert("Masukkan Kode Tiket terlebih dahulu!");
                return;
            }

            try {
                const response = await fetch(`/api/cek-status?tiket=${encodeURIComponent(kodeInput)}`);
                const data = await response.json();

                if (hasil) hasil.classList.remove('hidden');
                
                const tampilKode = document.getElementById('tampilKode');
                const statusBadge = document.getElementById('tampilStatus');
                const pesanBK = document.getElementById('pesanBK');

                if (tampilKode) tampilKode.innerText = kodeInput;

                if (response.ok) {
                    if (statusBadge) {
                        statusBadge.innerText = data.status;
                        statusBadge.className = "bg-yellow-100 text-yellow-800 font-bold px-4 py-2 rounded-lg inline-block";
                    }
                    if (pesanBK) {
                        pesanBK.innerText = `"${data.pesan_bk || data.pesanBK || 'Belum ada pesan dari Guru BK.'}"`;
                    }
                } else {
                    if (statusBadge) {
                        statusBadge.innerText = "Tiket Tidak Ditemukan";
                        statusBadge.className = "bg-red-100 text-red-800 font-bold px-4 py-2 rounded-lg inline-block";
                    }
                    if (pesanBK) {
                        pesanBK.innerText = "-";
                    }
                }
            } catch (err) {
                console.error("API Request Error:", err);
                alert("Gagal menghubungi server backend untuk mengecek status tiket.");
            }
        });
    }

    // --- E. SET HALAMAN DEFAULT KE HOME ---
    showPage('home');
});