"use strict";

(function () {
    window.addEventListener("load", init);

    const URL = "https://www.scrape-insight.com"
    const MONTH = 2592000000;

    google.charts.load('current', {'packages':['corechart', 'geochart', 'table', 'gauge']});

    async function init() {
        qs("#register form").addEventListener("submit", makeRegisterRequest);
        qs("#login form").addEventListener("submit", makeLoginRequest);
        qs("#login > button").addEventListener("click", displayRegister);
        qs("#register > button").addEventListener("click", displayLogin);
        qs("#textbox input").addEventListener("change", toggleSubmit);
        id("textbox").addEventListener("submit", makeRequest);
        id("signout-btn").addEventListener("click", signOut);
        id("clear-btn").addEventListener("click", () => {
            let result = confirm("Are you sure you want to clear all history?");
            if (result) {
                clearHistory();
            } 
        });
        id("account-btn").addEventListener("click", displayAccount);
        id("home-btn").addEventListener("click", displayHome);

        await checkCookie();
    }

    async function makeAccountRequest(username) {
        let res = await fetch(URL + "/account/" + username);
        await statusCheck(res);
        res = await res.text();
        return res;
    }

    function setCookie(name, value, options = {}) {
        let cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;
    
        if (options.expires) {
            cookie += `; expires=${options.expires}`;
        }
        if (options.path) {
            cookie += `; path=${options.path}`;
        }
        if (options.domain) {
            cookie += `; domain=${options.domain}`;
        }
        if (options.secure) {
            cookie += `; secure`;
        }
        if (options.sameSite) {
            cookie += `; SameSite=${options.sameSite}`;
        }
    
        document.cookie = cookie;
    }

    function getCookie(name) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            let [cookieName, cookieValue] = cookie.split('=').map(c => c.trim());
            if (cookieName === encodeURIComponent(name)) {
                return decodeURIComponent(cookieValue);
            }
        }
        return null;
    }

    function deleteCookie(name) {
        document.cookie = `${encodeURIComponent(name)}=; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }

    async function clearHistory() {
        try {
            let params = new FormData();
            params.append("username", getCookie("username"));
            let res = await fetch(URL + "/clear", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
            await makeChatRequest();
            id("chat").innerHTML = "";
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    async function checkCookie() {
        if (getCookie("username")) {
            await displayHome();
            if (getCookie("username") === "test") {
                let fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.id = "file-input";
                id("textbox").appendChild(fileInput);
                fileInput.addEventListener("change", feedQuestions);
            }
        } else {
            displayLogin();
        }
    }

    async function displayAccount() {
        id("home").classList.add("hidden");
        id("login").classList.add("hidden");
        id("register").classList.add("hidden");
        id("account").classList.remove("hidden");
        qs("body > section:nth-child(1)").style.display = "flex";

        let accountInfo = qsa("#account p");
        accountInfo[0].textContent = "Username: " + getCookie("username");
        let email = await makeAccountRequest(getCookie("username"));
        accountInfo[1].textContent = "Email: " + email;
    }

    function displayLogin() {
        id("home").classList.add("hidden");
        id("login").classList.remove("hidden");
        id("register").classList.add("hidden");
        id("account").classList.add("hidden");
        qs("body > section:nth-child(1)").style.display = "flex";
    }

    async function signOut() {
        deleteCookie("username");
        await checkCookie();
    }

    function displayRegister() {
        id("home").classList.add("hidden");
        id("login").classList.add("hidden");
        id("register").classList.remove("hidden");
        id("account").classList.add("hidden");
        qs("body > section:nth-child(1)").style.display = "flex";
    }

    async function displayHome() {
        id("home").classList.remove("hidden");
        id("login").classList.add("hidden");
        id("register").classList.add("hidden");
        id("chat").innerHTML = "";
        id("account").classList.add("hidden");
        qs("body > section:nth-child(1)").style.display = "none";

        await makeChatRequest();
    }

    async function makeChatRequest() {
        try {
            let username = getCookie("username");
            let res = await fetch(URL + "/get-all-chat/" + username);
            await statusCheck(res);
            res = await res.json();
            populateSidebar(res);
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    function populateSidebar(res) {
        id("sidebar").innerHTML = "";

        let data = {};
        
        for (let i = 0; i < res.length; i++) {
            let date = res[i][4];
            if (!data[date]) {
                data[date] = [];
            } 
            data[date].push(res[i]);
        }

        for (let date in data) {
            let dateTitle = document.createElement("h2");
            dateTitle.textContent = date;
            dateTitle.addEventListener("click", ()=> {
                populateChat(data[date]);
            });
            for (let i = 0; i < data[date].length; i++) {
                let queryTitle = document.createElement("h3");
                queryTitle.textContent = data[date][i][2];
                queryTitle.addEventListener("click", () => {
                    populateChat([data[date][i]]);
                });
                queryTitle.addEventListener("dblclick", async () => {
                    await deleteChat(data[date][i][0]);
                });
                id("sidebar").prepend(queryTitle);
            }
            id("sidebar").prepend(dateTitle);
        }
    }

    async function deleteChat(id) {
        try {
            let params = new FormData();
            params.append("id", id);
            let res = await fetch(URL + "/delete", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
            await makeChatRequest();
        } catch (err) {
            handleError();
        }
    }
    function populateChat(res) {
        id("chat").innerHTML = "";
        for(let i = 0; i < res.length; i++) {
            try {
                let entry = res[i];
                let chatId = entry[0];
                let question = entry[2];
                let response = entry[3];
                let data = entry[6];
                let format = entry[7];
                displayEntry(question, false);
                let chartBox = displayEntry(response, true, JSON.parse(entry[5]), question, chatId);
                if (data) {
                    generateChart(question, data, format, chartBox, chatId);
                } else {
                    chartBox.remove();
                }
            } catch (err) {
                console.log(err);
                continue;
            }
        }
    }

    function setExpirationDate() {
        let expirationDate = new Date();
        expirationDate.setTime(expirationDate.getTime() + MONTH);

        let expires = expirationDate.toUTCString();

        return expires;
    }

    async function makeRegisterRequest(e) {
        try {
            e.preventDefault();
            let params = new FormData(qs("#register form"));
            let res = await fetch(URL + "/register", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
            let username = qs("#register form input").value;
            let inputs = qsa("#register form input");
            inputs.forEach(input => {
                input.value = "";
            });
            setCookie("username", username, {expires: setExpirationDate()});
            await displayHome();
        } catch (err) {
            console.log(err);
            displayLoginError();
        }
    }

    async function makeLoginRequest(e) {
        try {
            e.preventDefault();
            let params = new FormData(qs("#login form"));
            let res = await fetch(URL + "/login", {
                method: "POST",
                body: params
            });
            qsa("#login-form input")[1].value = "";
            await statusCheck(res);
            let username = qs("#login form input").value;
            setCookie("username", username, {expires: setExpirationDate()});
            await displayHome();
        } catch (err) {
            console.log(err);
            displayLoginError();
        }
    }

    function toggleSubmit() {
        let button = qs("#textbox button");
        if (this.value.replaceAll(" ", "")){
            button.disabled = false;
        } else {
            button.disabled = true;
        }
    }

    async function makeRequest(e) {
        try{
            e.preventDefault();
            let query = qs("#textbox input").value;
            displayEntry(query, false);
            await generateResponse(query);

            qs("#textbox button").disabled = false;
            qs("#textbox input").value = "";
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    async function generateResponse(query) {
        let loading = displayLoading();
        qs("#textbox button").disabled = true;
        let username = getCookie("username");
        let params = new FormData();
        params.append("query", query);
        params.append("username", username);
        let res = await fetch(URL + "/getresponse", {
            method: "POST",
            body: params
        });
        await statusCheck(res);
        res = await res.json();
        let textResponse = res[0];
        let dataResponse = res[1];
        let format = res[2];
        let links = res[3];
        let chatId = res[4];
        loading.remove();
        let chartBox = displayEntry(textResponse, true, links, query);
        if (dataResponse) {
            try {
                generateChart(query, dataResponse, format, chartBox, chatId);
            } catch (err) {

            }
        } else {
            chartBox.remove();
        }
        await makeChatRequest();
    }

    function displayLoading() {
        let resTextbox = document.createElement("article");
        let aiImage = document.createElement("img");
        aiImage.src = "static/images/AI.png";
        resTextbox.prepend(aiImage);

        let loadingImage = document.createElement("img");
        loadingImage.src = "static/images/loading.gif";
        resTextbox.appendChild(loadingImage);
        resTextbox.classList.add("chat-entry");
        resTextbox.classList.add("response");
        resTextbox.classList.add("shadow");

        id("chat").appendChild(resTextbox);
        id("chat").scrollTop = id("chat").scrollHeight;

        return resTextbox;
    }

    function displayEntry(res, response, links=null, query=null, chatId=null) {
        let resTextbox = document.createElement("article");
        let text = document.createElement("p");
        text.textContent = res;
        let linkBox = document.createElement("p");
        if (links) {
            populateLinks(linkBox, links);
        }

        let subTextbox = document.createElement("section");
        let chartBox = document.createElement("section");

        subTextbox.appendChild(text);
        subTextbox.classList.add("sub-textbox");
        subTextbox.appendChild(chartBox);
        subTextbox.appendChild(linkBox);

        resTextbox.appendChild(subTextbox);
        resTextbox.classList.add("chat-entry");
        if (response) {
            populateResponse(resTextbox, subTextbox, chartBox, query, chatId);
        } else {
            resTextbox.classList.add("question");
            let img = document.createElement("img");
            img.src = "static/images/user.png";
            resTextbox.appendChild(img);
        }
        resTextbox.classList.add("shadow");
        id("chat").appendChild(resTextbox);
        return chartBox;
    }

    function generateChart(query, dataResponse, format, chartBox, chatId) {
        dataResponse = dataResponse.replace(/\\/g, "");
        dataResponse = JSON.parse(dataResponse);
        checkLength(dataResponse);

        let data = google.visualization.arrayToDataTable(dataResponse);
        let chartHeight = 600;

        let options = {
            title: query,
            titleTextStyle: {
                fontSize: 20
            },
            height: 600,
            chartArea: {
              width: '60%', // Adjust the width of the chart area
              height: '70%' // Adjust the height of the chart area
            },
            legend: {
              position: 'top' // Position the legend at the top for more space
            },
            colors: ['#3366CC', '#DC3912', '#FF9900', '#109618', '#990099'], // Customize bar colors
            animation: {
              startup: true,
              duration: 1000,
              easing: 'out'
            }
        };

        let chart;
        if (format === "bar graph"){
            chartHeight = flexHeight(dataResponse.length - 1, options);
            chart = new google.visualization.BarChart(chartBox);
            options["bars"] = "horizontal";
            options["bar"] = {
                groupWidth: '80%'
            }
        } else if (format === "line graph") {
            chart = new google.visualization.LineChart(chartBox);
            options['curveType'] = 'function'; // Set curve type for line chart
            options['lineWidth'] = 2; // Set line width
        } else if (format === "pie chart") {
            chart = new google.visualization.PieChart(chartBox);
            options['pieSliceText'] = 'label'; // Show label on pie slices
            options['pieHole'] = 0.4; // Set pie hole (donut chart)
        } else if (format === "scatterplot") {
            chart = new google.visualization.ScatterChart(chartBox);
            options['pointSize'] = 5; // Set size of points
            options['legend'] = { position: 'none' }; // Hide legend
        } else if (format === "table") {
            chart = new google.visualization.Table(chartBox);
            chartHeight = flexHeight(dataResponse.length - 1, options);
            options['allowHtml'] = true; // Allows HTML in table cells
            options['showRowNumber'] = true; // Show row numbers
            options['cssClassNames'] = {
                headerRow: 'header-row',
                tableRow: 'table-row',
                oddTableRow: 'odd-table-row',
                selectedTableRow: 'selected-table-row',
                hoverTableRow: 'hover-table-row'
            };
        } else if (format === "area chart") {
            chart = new google.visualization.AreaChart(chartBox);
            options['isStacked'] = true; // Stack area chart
        } else if (format === "bubble chart") {
            chart = new google.visualization.BubbleChart(chartBox);
            options['bubble'] = { opacity: 0.3 }; // Set bubble opacity
        } else if (format === "histogram") {
            chart = new google.visualization.Histogram(chartBox);
            options['histogram'] = { bucketSize: 1 }; // Set bucket size
        } else if (format === "geo chart") {
            chart = new google.visualization.GeoChart(chartBox);
            options['colorAxis'] = { colors: ['#e5f5f9', '#2ca25f'] }; // Set color axis range
        } else if (format === "donut chart") {
            chart = new google.visualization.PieChart(chartBox);
            options['pieHole'] = 0.4; // Set hole size for donut chart
        } else if (format === "gauge chart") {
            chart = new google.visualization.Gauge(chartBox);
            options['min'] = 0;
            options['max'] = 100;
            options['greenFrom'] = 80;
            options['greenTo'] = 100;
            options['yellowFrom'] = 60;
            options['yellowTo'] = 80;
            options['redFrom'] = 0;
            options['redTo'] = 60;
        } else {
            let error = document.createElement("p");
            error.textContent = "Graphic Type Not Supported Yet";
            error.classList.add("error");
            chartBox.appendChild(error);
        }

        chart.draw(data, options);
        chartBox.style.height = chartHeight + 50 + "px";

        populateChartButtons(chart, chartBox, chatId, dataResponse);
    }

    function populateChartButtons(chart, chartBox, chatId, dataResponse) {
        let buttonBox = document.createElement("section");
        let saveButton = document.createElement("button");
        saveButton.addEventListener("click", () => {
            console.log(chart.constructor.name);
            if (chart.constructor.name === "gvjs_hM") {
                saveTableAsCSV(dataResponse);
            } else {
                saveChartAsImage(chart);
            }
        });
        saveButton.textContent = "Download Chart";
        buttonBox.appendChild(saveButton);

        let driveImg = document.createElement("img");
        driveImg.src = "static/images/drive.png";
        driveImg.alt = "google drive logo";

        let uploadButton = document.createElement("button");
        uploadButton.addEventListener("click", async () => {
            let dataUrl;
            if (chart.constructor.name !== "gvjs_hM") {
                dataUrl = chart.getImageURI();
            } else {
                let csv = dataResponse.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
                let csvFile = new Blob([csv], { type: 'text/csv' });
                dataUrl = window.URL.createObjectURL(csvFile);
            }
            await makeUploadRequest(dataUrl, chatId);
        });
        uploadButton.textContent = "Upload Chart to Google Drive";
        uploadButton.appendChild(driveImg);
        buttonBox.appendChild(uploadButton);

        chartBox.appendChild(buttonBox);
    }

    async function makeUploadRequest(imgUrl, chatId) {
        try {
            let params = new FormData();
            params.append("id", chatId);
            let base64String = imgUrl.split(',')[1];
            params.append("image", base64String);
            let res = await fetch(URL + "/upload", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
        } catch (err) {
            window.location.href = URL + "/google";
        }

    }

    function populateLinks(linkBox, links) {
        // Create a text node for the initial text and the "References:" label
        linkBox.appendChild(document.createTextNode("\nReferences: "));
        for (let i = 0; i < links.length; i++) {
            // Create a text node for the link index and description
            linkBox.appendChild(document.createTextNode("\n" + (i + 1) + ") "));

            let urlElement = document.createElement("a");
            urlElement.href = links[i];
            urlElement.textContent = links[i];
            
            // Append the anchor element
            linkBox.appendChild(urlElement);
        }
    }

    function populateResponse(resTextbox, subTextbox, chartBox, query, chatId) {
        resTextbox.classList.add("response");
        let img = document.createElement("img");
        img.src = "static/images/AI.png";
        resTextbox.prepend(img);
        let buttonBox = document.createElement("section");
        let newAnswerButton = document.createElement("button");
        newAnswerButton.textContent = "Regenerate Response";
        newAnswerButton.addEventListener("click", () => {
            id("chat").appendChild(resTextbox.previousElementSibling);
            resTextbox.remove();
            generateResponse(query);
        });
        let deleteButton = document.createElement("button");
        deleteButton.textContent = "Delete Response";
        deleteButton.addEventListener("click", async () => {
            resTextbox.previousElementSibling.remove();
            resTextbox.remove();
            await deleteChat(chatId);
        })
        chartBox.classList.add("chart");
        buttonBox.appendChild(newAnswerButton);
        buttonBox.appendChild(deleteButton);

        buttonBox.classList.add("button-box");
        subTextbox.appendChild(buttonBox);
    }

    function checkLength(dataResponse) { // New function added
        let numColumns = dataResponse[0].length;
        for (let i = 0; i < dataResponse.length; i++) {
            if (dataResponse[i].length > numColumns) {
                dataResponse[i] = dataResponse[i].slice(0, numColumns);
            } else if (dataResponse[i].length < numColumns) {
                while (dataResponse[i].length < numColumns) {
                    dataResponse[i].push(null);
                }
            }
        }
    }

    function flexHeight(numRows, options) {
        let minHeight = 400;
        let additionalHeight = 30 * numRows;
        let chartHeight = Math.max(minHeight, minHeight + additionalHeight);
        options["height"] = chartHeight;
        return chartHeight;
    }

    function saveChartAsImage(chart) {
        let imgUrl = chart.getImageURI();
        let link = document.createElement("a");
        link.href = imgUrl;
        link.download = "chart.png";
        link.click();
    }

    function saveTableAsCSV(dataResponse) {
        let csv = dataResponse.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
        let csvFile = new Blob([csv], { type: 'text/csv' });
        let downloadLink = document.createElement('a');

        downloadLink.download = "table.csv";
        downloadLink.href = window.URL.createObjectURL(csvFile);
        downloadLink.style.display = 'none';

        document.body.appendChild(downloadLink);
        downloadLink.click();
    }

    async function feedQuestions(e) {
        try {
            e.preventDefault();
            let username = getCookie("username");
            let file = id("file-input").files[0];
            console.log(file);
            if (file) {
                let reader = new FileReader();
                reader.readAsText(file);
                reader.onload = function(e) {
                    console.log("inside");
                    let fileContent = e.target.result;
                    let lines = fileContent.split("\n");

                    lines.forEach(async (line, index) => {
                        let params = new FormData();
                        params.append("query", line);
                        params.append("username", username);
                        console.log(line);
                        let res = await fetch(URL + "/getresponse", {
                            method: "POST",
                            body: params
                        });
                        await statusCheck(res);
                    });
                }
            }
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    function handleError() {
        let error = document.createElement("p");
        error.textContent = "An Error Occured. Try Again Later!";
        error.classList.add("error");
        id("chat").appendChild(error);
    }

    function displayLoginError() {
        qs("#login p").classList.remove("hidden");
        qs("#register p").classList.remove("hidden");
        setTimeout(() => {
            qs("#login p").classList.add("hidden");
            qs("#register p").classList.add("hidden");
        }, 3000);
    }

    /**
     * Returns the element that has the ID attribute with the specified value.
     * @param {string} id - element ID.
     * @returns {object} - DOM object associated with id.
     */
    function id(id) {
        return document.getElementById(id);
    }

    /**
     * Returns first element matching selector.
     * @param {string} selector - CSS query selector.
     * @returns {object} - DOM object associated selector.
     */
    function qs(selector) {
        return document.querySelector(selector);
    }

    /**
     * Returns the array of elements that match the given CSS selector.
     * @param {string} query - CSS query selector
     * @returns {object[]} array of DOM objects matching the query.
     */
    function qsa(query) {
        return document.querySelectorAll(query);
    }

    /**
     * Helper function to return the response's result text if successful, otherwise
     * returns the rejected Promise result with an error status and corresponding text
     * @param {object} res - response to check for success/error
     * @return {object} - valid response if response was successful, otherwise rejected
     *                    Promise result
     */
    async function statusCheck(res) {
        if (!res.ok) {
        throw new Error(await res.text());
        }
        return res;
    }
})()