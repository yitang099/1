<?php
header('Content-Type: text/plain; charset=utf-8');
$pdo = new PDO('mysql:host=localhost;dbname=www_biobasebaby;charset=utf8', 'root', 'BkLab@Bao&yu255');
echo "=== yzn_member ===\n";
foreach ($pdo->query("SELECT username,nickname,email,mobile FROM yzn_member LIMIT 3") as $r) {
    print_r($r);
}
echo "\n=== yzn_form_message ===\n";
foreach ($pdo->query("SELECT messageusername,messageuserphone,messageuseremail FROM yzn_form_message WHERE messageuserphone REGEXP '^1[3-9]' LIMIT 3") as $r) {
    print_r($r);
}
