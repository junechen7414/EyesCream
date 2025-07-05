document.addEventListener('DOMContentLoaded', () => {
    // --- 狀態 (State) ---
    const images = [
      'https://images.unsplash.com/photo-1682687220247-9f786e34d472?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=1920',
      'https://images.unsplash.com/photo-1700162433346-4853c104818c?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=1920',
      'https://images.unsplash.com/photo-1699491712423-76a7599b5959?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=1920',
      'https://images.unsplash.com/photo-1700223889311-5cb524344389?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=1920',
      'https://images.unsplash.com/photo-1699743216235-3147a353c54c?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=1920',
    ];
    let currentIndex = 0;
    let autoplaySpeed = 3000;
    let autoplayIntervalId = null;

    // --- DOM 元素 ---
    const galleryContainer = document.getElementById('gallery-container');
    const mainImage = document.getElementById('main-image');
    const prevButton = document.getElementById('prev-button');
    const nextButton = document.getElementById('next-button');
    const speedSelect = document.getElementById('speed-select');
    const progressSlider = document.getElementById('progress-slider');
    const imageCounter = document.getElementById('image-counter');

    // --- 核心函式：更新所有 UI 元素 ---
    function updateGallery(isInstant = false) {
        if (images.length === 0) return;

        const showNewImage = () => {
            mainImage.src = images[currentIndex];
            progressSlider.value = currentIndex;
            imageCounter.textContent = `${currentIndex + 1} / ${images.length}`;
            mainImage.classList.remove('fade');
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
        if (e.key === 'ArrowRight' || e.key === 'PageDown') {
            nextImage();
        } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
            prevImage();
        }
    });

    // --- 初始化 ---
    function init() {
        progressSlider.max = images.length - 1;
        updateGallery(true); // 首次載入，立即顯示
        startAutoplay();
        galleryContainer.focus();
    }

    init();
});
