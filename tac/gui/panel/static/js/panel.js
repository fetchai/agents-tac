(function() {

    let currentSandboxID = null;

    let configureSandboxForm = function(){

        let form = document.getElementById("form-sandbox");
        let startBtn = document.getElementById("btn-start-sandbox");
        let stopBtn = document.getElementById("btn-stop-sandbox");

        stopBtn.disabled = true;

        form.addEventListener("submit", function (ev) {
            ev.preventDefault();

            let clickedBtnId = ev.target.target;
            if(clickedBtnId === startBtn.id){
                // start sandbox button clicked
                startSandbox();
            }
            else if(clickedBtnId === stopBtn.id){
                // stop sandbox button clicked
                stopSandbox();
            }

        });

        let startSandbox = function(){
            let XHR = new XMLHttpRequest();

            // Bind the FormData object and the form element
            let FD = new FormData(form);

            // Define what happens on successful data submission
            XHR.addEventListener("load", function (event) {
                startBtn.disabled = true;
                stopBtn.disabled = false;
            });

            // Define what happens in case of error
            XHR.addEventListener("error", function (event) {
                alert('ERROR: could not start sandbox.');
                startBtn.disabled = false;
                stopBtn.disabled = true;
            });

            XHR.open("POST", "/api/sandboxes", false);
            XHR.send(FD);
            let jsonResponse = JSON.parse(XHR.responseText);
            console.log(jsonResponse);
            currentSandboxID = jsonResponse["id"];
            return XHR.responseText;
        };

        let stopSandbox = function(){
            let XHR = new XMLHttpRequest();

            // Bind the FormData object and the form element
            let FD = new FormData(form);

            // Define what happens on successful data submission
            XHR.addEventListener("load", function (event) {
                startBtn.disabled = false;
                stopBtn.disabled = true;
            });

            // Define what happens in case of error
            XHR.addEventListener("error", function (event) {
                alert('ERROR: could not stop sandbox.');
                startBtn.disabled = true;
                stopBtn.disabled = false;
            });

            XHR.open("DELETE", "/api/sandboxes/" + currentSandboxID, true);
            XHR.send(FD);
            return XHR.responseText;
        };
    };

    let configureAgentForm = function(){
        let form = document.getElementById("form-agent");
        let startBtn = document.getElementById("btn-start-agent");
        let stopBtn = document.getElementById("btn-stop-agent");

        stopBtn.disabled = true;

        form.addEventListener("submit", function (ev) {
            ev.preventDefault();

            let clickedBtnId = ev.target.target;
            if(clickedBtnId === startBtn.id){
                // start agent button clicked
                startAgent();
            }
            else if(clickedBtnId === stopBtn.id){
                // stop sandbox button clicked
                stopAgent();
            }

        });

        let startAgent = function(){
            let XHR = new XMLHttpRequest();

            // Bind the FormData object and the form element
            let FD = new FormData(form);

            // Define what happens on successful data submission
            XHR.addEventListener("load", function (event) {
                startBtn.disabled = true;
                stopBtn.disabled = false;
            });

            // Define what happens in case of error
            XHR.addEventListener("error", function (event) {
                alert('ERROR: could not start agent.');
                startBtn.disabled = false;
                stopBtn.disabled = true;
            });

            XHR.open("POST", "/api/agent", true);
            XHR.send(FD);
            return XHR.responseText;
        };

        let stopAgent = function(){
            let XHR = new XMLHttpRequest();

            // Bind the FormData object and the form element
            let FD = new FormData(form);

            // Define what happens on successful data submission
            XHR.addEventListener("load", function (event) {
                startBtn.disabled = false;
                stopBtn.disabled = true;
            });

            // Define what happens in case of error
            XHR.addEventListener("error", function (event) {
                alert('ERROR: could not stop agent.');
                startBtn.disabled = true;
                stopBtn.disabled = false;
            });

            XHR.open("DELETE", "/api/agent", true);
            XHR.send(FD);
            return XHR.responseText;
        };

    };

    window.addEventListener("load", function () {
        configureSandboxForm();
        configureAgentForm();
    });



})();


