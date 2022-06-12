fetch('https://api.db-ip.com/v2/free/self', { mode: 'cors' })
.then((response) => {
    if (!response.ok)
        return null;
    return response.json();
})
.then((data) => {
    if (data == null)
        return;

    var ip = { my_ip : data.ipAddress };
    chrome.storage.sync.set(ip, () => { console.log(ip); });
});


// Пример отправки POST запроса:
async function postData(url = '', data = {}) {
    // Default options are marked with *
    const response = await fetch(url, {
        method: 'PUT', // *GET, POST, PUT, DELETE, etc.
        mode: 'cors', // no-cors, *cors, same-origin
        cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
        credentials: 'same-origin', // include, *same-origin, omit
        headers: {
            'Content-Type': 'application/json'
        },
        redirect: 'follow', // manual, *follow, error
        referrerPolicy: 'no-referrer', // no-referrer, *client
        body: JSON.stringify(data) // body data type must match "Content-Type" header
    });
    
    return await response.json();
}


setInterval(() => {
    var tm = document.getElementById('ct');
    if (tm == null || tm == undefined)
        return;

    var num = tm.innerHTML;
    console.log("Time: " + num);
    var datetime = new Date('1970-01-01T' + num + 'Z');

    chrome.storage.sync.get("my_ip", (item) => {
        if (item.my_ip == null || item.my_ip == undefined)
            return;

        var ip = item.my_ip.replace(/\./gi, '');
        console.log(ip);

        postData('https://queue-a2e1e-default-rtdb.europe-west1.firebasedatabase.app/browsers/' + ip + '.json', {
            ip : item.my_ip,
            time : datetime
        })
        .then((data) => {
            console.log(data);
        });
    });
}, 15000);