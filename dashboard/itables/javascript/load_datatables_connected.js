require.config({
    paths: {
        datatables: 'https://cdn.datatables.net/1.10.19/js/jquery.dataTables.min',
    }
});
$('head').append('<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>');

$('head').append('<link rel="stylesheet" type="text/css" \
                href = "https://cdn.datatables.net/1.10.19/css/jquery.dataTables.min.css" > ');

$('head').append('<style> table td { text-overflow: ellipsis; overflow: hidden; } </style>');
