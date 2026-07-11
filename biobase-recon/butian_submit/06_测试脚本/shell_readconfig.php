<?php
header('Content-Type: text/plain; charset=utf-8');
echo file_get_contents('/var/www/www.biobasebaby.com/config/database.php');
