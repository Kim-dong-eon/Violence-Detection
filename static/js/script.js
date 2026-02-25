function navigateTo(page) {
    if (page === 'cctv') {
        window.location.href = '/cctv'; // CCTV 바로가기 페이지로 이동
    } else if (page === 'videos') {
        window.location.href = '/videos'; // 녹화 영상 페이지로 이동
    }
}
