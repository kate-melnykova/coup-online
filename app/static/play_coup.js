$(document).ready(function(){
});

function verifyAmbassador(){
{
    var n_cards = document.getElementsById("n_cards");
    if (n_cards == null){
        console.log('Not ambassador');
        return 0
    } else {
        var checkboxes = document.getElementsByName("selected_cards");
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

function loadState() {
    window.setTimeout(function(){
        location.reload()
    }, 2000);
}
