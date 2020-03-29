$(document).ready(function(){
    loadState();
});

function loadState() {
    window.setTimeout(function(){
        $.ajax({
            url: '/waiting',
            method: 'POST',
            dataType: 'json',
            success: function(result){
                if (result.url){
                    console.log(result.url);
                    if (result.url){
                    console.log('True');
                    }
                    window.location.href = result.url;
                } else {
                    loadState();
                }
            },
        });
    }, 2000);
}
