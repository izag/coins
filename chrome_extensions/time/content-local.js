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
        method: 'POST', // *GET, POST, PUT, DELETE, etc.
        mode: 'no-cors', // no-cors, *cors, same-origin
        // cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
        // credentials: 'same-origin', // include, *same-origin, omit
        // headers: {
        //     "Accept": "application/json",
        //     "Content-type": "application/json"
        // },
        // redirect: 'follow', // manual, *follow, error
        // referrerPolicy: 'no-referrer', // no-referrer, *client
        body: JSON.stringify(data) // body data type must match "Content-Type" header
    });
    
    return response;
}


setInterval(() => {
    const tm = document.getElementById('ct');
    if (tm == null)
        return;

    const num = tm.innerHTML;
    console.log("Time: " + num);
    const datetime = new Date('1970-01-01T' + num + 'Z');

    chrome.storage.sync.get("my_ip", (item) => {
        if (item.my_ip == null)
            return;

        const ip = item.my_ip.replace(/\./gi, '');
        console.log(ip);

        postData('http://localhost:8888/browsers', {
            ip : item.my_ip,
            time : datetime
        })
        .then((data) => {
            console.log(data);
        });
    });
}, 15000);