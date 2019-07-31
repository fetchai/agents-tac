(function() {


    let configureSandboxForm = function(){

        let form = document.getElementById("form-sandbox");
        let startSandboxBtn = document.getElementById("btn-start-sandbox");
        let stopSandboxBtn = document.getElementById("btn-stop-sandbox");

        stopSandboxBtn.disabled = true;

        form.addEventListener("submit", function (ev) {
            ev.preventDefault();

            let clickedBtnId = ev.target.target;
            console.log(clickedBtnId, " clicked");
            if(clickedBtnId === startSandboxBtn.id){
                // start sandbox button clicked
                startSandbox();
            }
            else if(clickedBtnId === stopSandboxBtn.id){
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
                startSandboxBtn.disabled = true;
                stopSandboxBtn.disabled = false;
            });

            // Define what happens in case of error
            XHR.addEventListener("error", function (event) {
                alert('ERROR: could not start sandbox.');
                startSandboxBtn.disabled = false;
                stopSandboxBtn.disabled = true;
            });

            XHR.open("POST", "/api/sandbox", true);
            XHR.send(FD);
            return XHR.responseText;
        };

        let stopSandbox = function(){
            let XHR = new XMLHttpRequest();

            // Bind the FormData object and the form element
            let FD = new FormData(form);

            // Define what happens on successful data submission
            XHR.addEventListener("load", function (event) {
                startSandboxBtn.disabled = false;
                stopSandboxBtn.disabled = true;
            });

            // Define what happens in case of error
            XHR.addEventListener("error", function (event) {
                alert('ERROR: could not stop sandbox.');
                startSandboxBtn.disabled = true;
                stopSandboxBtn.disabled = false;
            });

            XHR.open("DELETE", "/api/sandbox", true);
            XHR.send(FD);
            return XHR.responseText;
        };
    };


    window.addEventListener("load", function () {
        configureSandboxForm();
    });



})();


