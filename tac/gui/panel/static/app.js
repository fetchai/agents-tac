let startSandbox = function () {
    let body = $("#btn-start-sandbox").serialize();
    let xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "POST", "/api/sandboxes", false ); // false for synchronous request
    xmlHttp.send( body );
    return xmlHttp.responseText;
};
