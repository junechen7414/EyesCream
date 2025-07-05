document.addEventListener('DOMContentLoaded', async () => {
    // --- 狀態 (State) ---
    let images = [];
    let currentIndex = 0;
    let autoplaySpeed = 3000;
    let autoplayIntervalId = null;

    // --- 函式庫：從文字檔載入圖片 ---
    async function loadImagesFromTxt(filePath) {
        try {
            const response = await fetch(filePath);
            if (!response.ok) {
                throw new Error(`HTTP 錯誤！ 狀態: ${response.status}`);
            }
            const text = await response.text();
            return text.split('\n').filter(url => url.trim() !== '');
        } catch (error) {
            console.error('無法載入圖片列表檔案:', error);
            galleryContainer.innerHTML = '<p style="color: red; text-align: center;">無法載入圖片列表，請檢查 sample.txt 檔案是否存在且路徑正確。</p>';
            return [];
        }
    }

    // --- DOM 元素 ---
    const galleryContainer = document.getElementById('gallery-container');
    const mainImage = document.getElementById('main-image');
    const prevButton = document.getElementById('prev-button');
    const nextButton = document.getElementById('next-button');
    const speedSelect = document.getElementById('speed-select');
    const progressSlider = document.getElementById('progress-slider');
    const imageCounter = document.getElementById('image-counter');

    // --- 效能優化：預載入下一張圖片 ---
    function preloadNextImage() {
        if (images.length < 2) return; // 如果圖片少於2張，則無需預載入

        const nextIndex = (currentIndex + 1) % images.length;
        const preloadLink = document.createElement('link');
        preloadLink.rel = 'preload';
        preloadLink.as = 'image';
        preloadLink.href = images[nextIndex];
        document.head.appendChild(preloadLink);
        // 為了避免 head 標籤無限增長，可以在一段時間後移除它，但現代瀏覽器通常能很好地處理
    }

    // --- 核心函式：更新所有 UI 元素 ---
    function updateGallery(isInstant = false) {
        if (images.length === 0) return;

        const showNewImage = () => {
            mainImage.src = images[currentIndex];
            progressSlider.value = currentIndex;
            imageCounter.textContent = `${currentIndex + 1} / ${images.length}`;
            mainImage.classList.remove('fade');

            // 當新圖片顯示後，立即開始預載入下一張
            preloadNextImage();
        };

        if (isInstant) {
            showNewImage();
        } else {
            mainImage.classList.add('fade');
            // 等待淡出動畫完成後再更換圖片並淡入
            setTimeout(showNewImage, 400);
        }
    }

    // --- 導覽函式 ---
    const nextImage = () => {
        currentIndex = (currentIndex + 1) % images.length;
        updateGallery();
        resetAutoplay();
    };

    const prevImage = () => {
        currentIndex = (currentIndex - 1 + images.length) % images.length;
        updateGallery();
        resetAutoplay();
    };

    // --- 自動播放 ---
    const startAutoplay = () => {
        if (autoplayIntervalId) clearInterval(autoplayIntervalId);
        if (images.length > 1) {
            autoplayIntervalId = setInterval(nextImage, autoplaySpeed);
        }
    };

    const stopAutoplay = () => {
        clearInterval(autoplayIntervalId);
        autoplayIntervalId = null;
    };

    const resetAutoplay = () => {
        stopAutoplay();
        startAutoplay();
    };

    // --- 事件監聽器 ---
    prevButton.addEventListener('click', prevImage);
    nextButton.addEventListener('click', nextImage);
    mainImage.addEventListener('click', nextImage);

    speedSelect.addEventListener('change', (e) => {
        autoplaySpeed = parseInt(e.target.value, 10);
        resetAutoplay();
    });

    progressSlider.addEventListener('input', (e) => {
        currentIndex = parseInt(e.target.value, 10);
        updateGallery(true); // 拖動時立即更新，不加動畫
        resetAutoplay();
    });

    window.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === 'ArrowDown') {
            nextImage();
        } else if (e.key === 'ArrowLeft' || e.key === 'PageUp' || e.key === 'ArrowUp') {
            prevImage();
        }
    });

    // --- 初始化 ---
    function init() {
        if (images.length === 0) return; // 如果沒有圖片，則不進行初始化
        progressSlider.max = images.length - 1;
        updateGallery(true); // 首次載入，立即顯示
        startAutoplay();
        galleryContainer.focus();
    }

    // --- 應用程式啟動 ---
    images = await loadImagesFromTxt('sample.txt');
    init();
});
