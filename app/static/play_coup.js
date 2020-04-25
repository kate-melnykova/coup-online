$(document).ready(function(){
    loadState();
});

window.reload = function(data){
    window.location.href = data.url;
}

function loadState() {
    window.setTimeout(function(){
        $.ajax({
            url: '/long_polling',
            method: 'GET',
            dataType: 'json',
            success: function(event){
                window[event.type](event.data);
                loadState();
            }
        });
    }, 2000);
}

function verifyAmbassador(){
{
    var n_cards = $("#n_cards");
    if (n_cards == null){
        console.log('Not ambassador');
        return 0
    } else {
        var checkboxes = $("[name=selected_cards]");
        var numberOfCheckedItems = 0;
        for(var i = 0; i < checkboxes.length; i++)
        {
            if(checkboxes[i].checked)
                numberOfCheckedItems++;
        }
        if (numberOfCheckedItems != 2)
        {
            alert('You selected not ' + n_cards + ' cards!');
            return -1
        }
    };
    return 1
}
};

