const translations = {
    en: {
        title: "YouTube Video Analyzer",
        subtitle: "Analyze and download YouTube videos",
        urlPlaceholder: "Enter YouTube video URL",
        analyzeButton: "Analyze Video",
        resultsTitle: "Scene Analysis Results",
        downloadSelected: "Download Selected Scenes",
        downloadAll: "Download All Scenes",
        videoInfo: "Video Information",
        selectAll: "Select All",
        deselectAll: "Deselect All",
        noSceneSelected: "Please select at least one scene"
    },
    vi: {
        title: "Công cụ Phân tích Video YouTube",
        subtitle: "Phân tích và tải xuống video YouTube",
        urlPlaceholder: "Nhập URL video YouTube",
        analyzeButton: "Phân tích Video",
        resultsTitle: "Kết quả Phân tích Cảnh",
        downloadSelected: "Tải Cảnh Đã Chọn",
        downloadAll: "Tải Tất cả Cảnh",
        videoInfo: "Thông tin Video",
        selectAll: "Chọn Tất cả",
        deselectAll: "Bỏ chọn Tất cả",
        noSceneSelected: "Vui lòng chọn ít nhất một cảnh"
    },
    ar: {
        title: "محلل فيديو يوتيوب",
        subtitle: "تحليل وتحميل مقاطع فيديو يوتيوب",
        urlPlaceholder: "أدخل رابط فيديو يوتيوب",
        analyzeButton: "تحليل الفيديو",
        resultsTitle: "نتائج تحليل المشاهد",
        downloadSelected: "تحميل المشاهد المحددة",
        downloadAll: "تحميل جميع المشاهد",
        videoInfo: "معلومات الفيديو",
        selectAll: "تحديد الكل",
        deselectAll: "إلغاء تحديد الكل",
        noSceneSelected: "الرجاء تحديد مشهد واحد على الأقل"
    },
    "ar-ma": {
        title: "محلل فيديو يوتيوب",
        subtitle: "تحليل وتحميل فيديوهات يوتيوب",
        urlPlaceholder: "دخل رابط الفيديو",
        analyzeButton: "تحليل الفيديو",
        resultsTitle: "نتائج تحليل المشاهد",
        downloadSelected: "تحميل المشاهد المختارة",
        downloadAll: "تحميل جميع المشاهد",
        videoInfo: "معلومات الفيديو",
        selectAll: "اختيار الكل",
        deselectAll: "إلغاء اختيار الكل",
        noSceneSelected: "المرجو اختيار مشهد واحد على الأقل"
    }
};

function changeLanguage() {
    const lang = document.getElementById('languageSelect').value;
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        element.textContent = translations[lang][key];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        element.placeholder = translations[lang][key];
    });
}

// 初始化语言
document.addEventListener('DOMContentLoaded', () => {
    changeLanguage();
}); 