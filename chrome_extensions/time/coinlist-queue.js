fetch('https://api.db-ip.com/v2/free/self', { mode: 'cors' })
.then((response) => {
    if (!response.ok)
        return null;
    return response.json();
})
.then((data) => {
    if (data == null)
        return;

    const ip = {my_ip: data.ipAddress};
    chrome.storage.sync.set(ip, () => { console.log(ip); });
});


// Пример отправки POST запроса:
async function postData(url = '', data = {}) {
    // Default options are marked with *
    const response = await fetch(url, {
        method: 'POST', // *GET, POST, PUT, DELETE, etc.
        mode: 'no-cors', // no-cors, *cors, same-origin
        body: JSON.stringify(data) // body data type must match "Content-Type" header
    });

    return response;
}


setInterval(() => {
    const val = document.getElementById('MainPart_lbUsersInLineAheadOfYou');
    if (val == null)
        return;

    const num = val.innerHTML;
    chrome.storage.sync.get("my_ip", (item) => {
        if (item.my_ip == null)
            return;

        const ip = item.my_ip.replace(/\./gi, '');
        console.log(ip);

        postData('http://localhost:8888/browsers', {
            ip : item.my_ip,
            position : num
        })
        .then((data) => {
            console.log(data);
        });
    });
}, 15000);