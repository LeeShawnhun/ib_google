document.addEventListener('DOMContentLoaded', (event) => {
    const form = document.querySelector('form');
    const fileInput = document.querySelector('input[type="file"]');

    form.addEventListener('submit', (e) => {
        if (fileInput.files.length === 0) {
            e.preventDefault();
            alert('하나 이상의 파일을 업로드 해주세요!');
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');

    fileInput.addEventListener('change', function(e) {
        fileList.innerHTML = '';
        for (let i = 0; i < this.files.length; i++) {
            let file = this.files[i];
            let listItem = document.createElement('div');
            listItem.textContent = file.name;
            fileList.appendChild(listItem);
        }
    });

});