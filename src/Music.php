<?php declare(strict_types=1);
class Music
{
    // http://ubeat.herokuapp.com/unsecure/artists/3941697
    private $base_url = "http://ubeat.herokuapp.com/unsecure/";

    public function getArtist($artistId)
    {
        $artist_url = "{$this->base_url}artists/{$artistId}";
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_URL, $artist_url);
        $response = curl_exec($ch);
        curl_close($ch);
        return json_decode($response, true)['results'][0];
    }
 
}