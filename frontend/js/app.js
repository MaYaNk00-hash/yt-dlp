/**
 * yt-dlp Studio | Vanilla JavaScript Interactive Controller
 * Handles stream analysis, DOM rendering, format filtering, and WebSocket download streaming.
 */

class ToastManager {
    constructor() {
        this.container = document.getElementById('toast-container');
    }

    show(message, type = 'info', duration = 4500) {
        const toast = document.createElement('div');
        toast.className = `toast-message ${type}`;
        
        let iconSvg = '';
        if (type === 'success') {
            iconSvg = `<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
        } else if (type === 'error') {
            iconSvg = `<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2.5" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
        } else {
            iconSvg = `<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2.5" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        }

        toast.innerHTML = `
            <div class="toast-icon">${iconSvg}</div>
            <div class="toast-text">${message}</div>
        `;
        
        this.container.appendChild(toast);

        setTimeout(() => {
            toast.style.transition = 'all 0.3s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

class YtDlpStudio {
    constructor() {
        this.toast = new ToastManager();
        this.currentVideoData = null;
        this.currentFilter = 'Top 5 Combined';
        this.activeWebSocket = null;
        this.loadingQuotes = [
            { title: "Extracting Stream Manifests...", sub: "Connecting to target host and analyzing audio & video quality profiles" },
            { title: "Inspecting Codec Profiles...", sub: "Unraveling VP9, AV1, H.264 video tracks and Opus/AAC audio streams" },
            { title: "Curating Top Combined Streams...", sub: "Pairing top high definition video feeds with maximum audio bitrate" },
        ];
        this.quoteInterval = null;

        this.initElements();
        this.initEventListeners();
    }

    initElements() {
        this.urlInput = document.getElementById('url-input');
        this.clearBtn = document.getElementById('clear-btn');
        this.pasteBtn = document.getElementById('paste-btn');
        this.analyzeBtn = document.getElementById('analyze-btn');
        
        this.loadingSection = document.getElementById('loading-section');
        this.loaderTitle = document.getElementById('loader-title');
        this.loaderSubtitle = document.getElementById('loader-subtitle');
        
        this.resultsSection = document.getElementById('results-section');
        this.videoThumbnail = document.getElementById('video-thumbnail');
        this.videoDuration = document.getElementById('video-duration');
        this.videoOutlink = document.getElementById('video-outlink');
        this.videoTitle = document.getElementById('video-title');
        this.videoUploader = document.getElementById('video-uploader');
        this.totalFormatsTag = document.getElementById('total-formats-tag');
        
        this.filterButtons = document.querySelectorAll('.filter-btn');
        this.formatsGrid = document.getElementById('formats-grid');
        
        // Download drawer elements
        this.drawer = document.getElementById('download-drawer');
        this.drawerStatusText = document.getElementById('drawer-status-text');
        this.drawerItemTitle = document.getElementById('drawer-item-title');
        this.drawerIcon = document.getElementById('drawer-icon');
        this.saveFileBtn = document.getElementById('save-file-btn');
        this.closeDrawerBtn = document.getElementById('close-drawer-btn');
        this.progressBarFill = document.getElementById('progress-bar-fill');
        this.progressPercent = document.getElementById('progress-percent');
        this.progressSpeed = document.getElementById('progress-speed');
        this.progressEta = document.getElementById('progress-eta');
    }

    initEventListeners() {
        this.urlInput.addEventListener('input', () => {
            this.clearBtn.style.display = this.urlInput.value ? 'flex' : 'none';
        });

        this.clearBtn.addEventListener('click', () => {
            this.urlInput.value = '';
            this.clearBtn.style.display = 'none';
            this.urlInput.focus();
        });

        this.pasteBtn.addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text) {
                    this.urlInput.value = text.trim();
                    this.clearBtn.style.display = 'flex';
                    this.analyzeUrl(this.urlInput.value);
                }
            } catch (err) {
                this.toast.show('Unable to access clipboard automatically. Please press Ctrl+V or Cmd+V to paste.', 'info');
            }
        });

        this.urlInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && this.urlInput.value.trim()) {
                this.analyzeUrl(this.urlInput.value.trim());
            }
        });

        this.analyzeBtn.addEventListener('click', () => {
            const url = this.urlInput.value.trim();
            if (!url) {
                this.toast.show('Please paste a supported video URL to analyze.', 'error');
                this.urlInput.focus();
                return;
            }
            this.analyzeUrl(url);
        });

        this.filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                this.filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.dataset.filter;
                this.renderFormatsList();
            });
        });

        this.closeDrawerBtn.addEventListener('click', () => {
            this.drawer.style.display = 'none';
        });
    }

    startLoadingState() {
        this.resultsSection.style.display = 'none';
        this.loadingSection.style.display = 'block';
        this.analyzeBtn.disabled = true;
        this.analyzeBtn.style.opacity = '0.7';

        let index = 0;
        this.loaderTitle.textContent = this.loadingQuotes[index].title;
        this.loaderSubtitle.textContent = this.loadingQuotes[index].sub;

        this.quoteInterval = setInterval(() => {
            index = (index + 1) % this.loadingQuotes.length;
            this.loaderTitle.textContent = this.loadingQuotes[index].title;
            this.loaderSubtitle.textContent = this.loadingQuotes[index].sub;
        }, 2200);
    }

    stopLoadingState() {
        clearInterval(this.quoteInterval);
        this.loadingSection.style.display = 'none';
        this.analyzeBtn.disabled = false;
        this.analyzeBtn.style.opacity = '1';
    }

    async analyzeUrl(url) {
        this.startLoadingState();
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || 'Failed to analyze video URL');
            }

            this.currentVideoData = result;
            this.stopLoadingState();
            this.renderVideoOverview();
            this.updateCategoryCounts();
            
            // Reset view to Top 5 Combined on new URL analysis
            this.currentFilter = 'Top 5 Combined';
            this.filterButtons.forEach(b => {
                b.classList.toggle('active', b.dataset.filter === 'Top 5 Combined');
            });
            
            this.renderFormatsList();
            this.resultsSection.style.display = 'block';
            
            setTimeout(() => {
                this.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);

            this.toast.show(`Successfully extracted stream profiles with Top 5 High Quality options!`, 'success');
        } catch (error) {
            this.stopLoadingState();
            this.toast.show(error.message, 'error', 6000);
        }
    }

    renderVideoOverview() {
        const data = this.currentVideoData;
        if (!data) return;

        this.videoTitle.textContent = data.title;
        this.videoUploader.textContent = data.uploader;
        this.videoDuration.textContent = `⏱️ ${data.duration_formatted}`;
        
        const rawCount = data.formats.filter(f => f.format_type !== 'Top 5 Combined').length;
        this.totalFormatsTag.textContent = `${rawCount} Raw Tracks + 5 Top Combined`;
        
        if (data.thumbnail) {
            this.videoThumbnail.src = data.thumbnail;
            this.videoThumbnail.style.display = 'block';
        } else {
            this.videoThumbnail.style.display = 'none';
        }

        this.videoOutlink.href = data.webpage_url || '#';
    }

    updateCategoryCounts() {
        const formats = this.currentVideoData.formats;
        const countTop = formats.filter(f => f.format_type === 'Top 5 Combined').length;
        const countVa = formats.filter(f => f.format_type === 'Video + Audio').length;
        const countVo = formats.filter(f => f.format_type === 'Video Only').length;
        const countAo = formats.filter(f => f.format_type === 'Audio Only').length;
        const countAll = formats.length;

        if (document.getElementById('count-top')) document.getElementById('count-top').textContent = countTop;
        if (document.getElementById('count-all')) document.getElementById('count-all').textContent = countAll;
        if (document.getElementById('count-va')) document.getElementById('count-va').textContent = countVa;
        if (document.getElementById('count-vo')) document.getElementById('count-vo').textContent = countVo;
        if (document.getElementById('count-ao')) document.getElementById('count-ao').textContent = countAo;
    }

    renderFormatsList() {
        const grid = this.formatsGrid;
        grid.innerHTML = '';

        const formats = this.currentVideoData.formats.filter(item => {
            if (this.currentFilter === 'All') return true;
            return item.format_type === this.currentFilter;
        });

        if (formats.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 3rem; text-align: center; color: var(--text-secondary); background: rgba(0,0,0,0.2); border-radius: 12px;">
                    No stream profiles found in category "${this.currentFilter}".
                </div>
            `;
            return;
        }

        formats.forEach(item => {
            const card = document.createElement('div');
            card.className = 'format-card';
            card.setAttribute('data-type', item.format_type);

            let badgeClass = 'badge-va';
            if (item.format_type === 'Top 5 Combined') badgeClass = 'badge-top';
            if (item.format_type === 'Video Only') badgeClass = 'badge-vo';
            if (item.format_type === 'Audio Only') badgeClass = 'badge-ao';

            const fpsStr = item.fps ? `${item.fps} fps` : '-';
            const cmdStr = item.command || `yt-dlp -f "${item.format_id}"`;
            
            let badgeText = item.format_type;
            if (item.format_type === 'Top 5 Combined') badgeText = '🏆 Top Combined';

            card.innerHTML = `
                <div>
                    <div class="card-top">
                        <span class="category-badge ${badgeClass}">${badgeText}</span>
                        <span class="ext-badge">${item.ext.toUpperCase()}</span>
                    </div>
                    <div class="card-title-area">
                        <div class="format-resolution">${item.resolution}</div>
                        <div class="format-note">ID: ${item.format_id} ${item.note ? ` • ${item.note}` : ''}</div>
                    </div>
                    <div class="command-box" title="Exact terminal command for this quality profile">
                        <code class="command-text">${cmdStr}</code>
                        <button type="button" class="copy-cmd-btn" title="Copy CLI Command to Clipboard">📋 Copy Cmd</button>
                    </div>
                    <div class="specs-grid">
                        <div class="spec-item">
                            <span class="spec-label">File Size</span>
                            <span class="spec-val">${item.filesize_str}</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">Frame Rate</span>
                            <span class="spec-val">${fpsStr}</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">Video Codec</span>
                            <span class="spec-val" title="${item.vcodec}">${item.vcodec}</span>
                        </div>
                        <div class="spec-item">
                            <span class="spec-label">Audio Codec</span>
                            <span class="spec-val" title="${item.acodec}">${item.acodec}</span>
                        </div>
                    </div>
                </div>
                <button type="button" class="download-action-btn" data-format='${JSON.stringify(item).replace(/'/g, "&apos;")}'>
                    <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    <span>Download Format</span>
                </button>
            `;

            const btn = card.querySelector('.download-action-btn');
            btn.addEventListener('click', () => {
                this.initiateDownload(item);
            });

            const copyBtn = card.querySelector('.copy-cmd-btn');
            if (copyBtn) {
                copyBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    try {
                        await navigator.clipboard.writeText(cmdStr);
                        this.toast.show('Terminal command copied to clipboard!', 'success', 2500);
                        copyBtn.textContent = '✅ Copied!';
                        copyBtn.style.color = '#10b981';
                        setTimeout(() => { 
                            copyBtn.textContent = '📋 Copy Cmd'; 
                            copyBtn.style.color = '';
                        }, 2000);
                    } catch (err) {
                        this.toast.show('Failed to copy command automatically.', 'error');
                    }
                });
            }

            grid.appendChild(card);
        });
    }

    async initiateDownload(formatItem) {
        if (!this.currentVideoData) return;

        const targetUrl = this.currentVideoData.webpage_url || this.urlInput.value.trim();

        try {
            this.toast.show(`Queueing download for ${formatItem.resolution} (${formatItem.ext.toUpperCase()})...`, 'info', 3000);
            
            const resp = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: targetUrl,
                    format_id: formatItem.format_id,
                    format_type: formatItem.format_type,
                    title: this.currentVideoData.title
                })
            });

            const data = await resp.json();
            if (!resp.ok) {
                throw new Error(data.detail || 'Failed to start background download');
            }

            this.openDownloadDrawer(formatItem, data.task_id, data.ws_url);
        } catch (error) {
            this.toast.show(`Download setup failed: ${error.message}`, 'error', 6000);
        }
    }

    openDownloadDrawer(formatItem, taskId, wsUrl) {
        this.drawerStatusText.textContent = 'Connecting to download engine...';
        this.drawerItemTitle.textContent = `${this.currentVideoData.title} (${formatItem.resolution})`;
        this.progressBarFill.style.width = '2%';
        this.progressPercent.textContent = '0.0%';
        this.progressSpeed.textContent = 'Connecting...';
        this.progressEta.textContent = 'ETA: -';
        this.saveFileBtn.style.display = 'none';
        this.drawerIcon.innerHTML = `
            <div class="pulse-ring"></div>
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
        `;

        this.drawer.style.display = 'block';

        if (this.activeWebSocket && this.activeWebSocket.readyState === WebSocket.OPEN) {
            this.activeWebSocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const fullWsUrl = `${protocol}//${window.location.host}${wsUrl}`;
        
        this.activeWebSocket = new WebSocket(fullWsUrl);

        this.activeWebSocket.onmessage = (event) => {
            const progress = JSON.parse(event.data);
            this.updateDownloadProgress(progress);
        };

        this.activeWebSocket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            this.toast.show('Real-time connection interruption. Download continues on server.', 'error');
        };
    }

    updateDownloadProgress(progress) {
        if (progress.status === 'downloading') {
            this.drawerStatusText.textContent = 'Downloading stream data...';
            this.progressBarFill.style.width = `${Math.max(progress.progress_percent, 2)}%`;
            this.progressPercent.textContent = `${progress.progress_percent}%`;
            this.progressSpeed.textContent = progress.speed_str || '-';
            this.progressEta.textContent = `ETA: ${progress.eta_str || '-'}`;
        } else if (progress.status === 'merging') {
            this.drawerStatusText.textContent = '⚙️ Merging Video & Audio with FFmpeg...';
            this.progressBarFill.style.width = '99%';
            this.progressPercent.textContent = '99% (Transcoding)';
            this.progressSpeed.textContent = 'FFmpeg processing';
            this.progressEta.textContent = 'Almost ready...';
            this.toast.show('Stream downloaded. Now automatically merging high quality audio & video with FFmpeg...', 'info', 3500);
        } else if (progress.status === 'complete') {
            this.drawerStatusText.textContent = '✅ Stream Download & Merge Complete!';
            this.progressBarFill.style.width = '100%';
            this.progressPercent.textContent = '100%';
            this.progressSpeed.textContent = 'Ready';
            this.progressEta.textContent = 'Finished';
            
            this.drawerIcon.innerHTML = `
                <svg viewBox="0 0 24 24" width="24" height="24" stroke="#10b981" stroke-width="2.5" fill="none">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
            `;

            this.saveFileBtn.style.display = 'inline-flex';
            this.saveFileBtn.onclick = () => {
                const a = document.createElement('a');
                a.href = progress.download_url;
                a.download = progress.filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            };

            setTimeout(() => {
                this.saveFileBtn.click();
            }, 300);

            this.toast.show('🎉 File has been saved to your device!', 'success', 5000);

            if (this.activeWebSocket) {
                this.activeWebSocket.close();
            }
        } else if (progress.status === 'error') {
            this.drawerStatusText.textContent = '❌ Download Failed';
            this.toast.show(progress.error_message || 'An error occurred during downloading.', 'error', 8000);
            if (this.activeWebSocket) {
                this.activeWebSocket.close();
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.ytStudio = new YtDlpStudio();
});
