<?php declare(strict_types=1);
use PHPUnit\Framework\TestCase;
 
class MusicFunctionalTest extends TestCase
{
    private $music;
 
    protected function setUp(): void
    {
        $this->music = new Music();
    }
 
    protected function tearDown(): void
    {
        $this->music = NULL;
    }
 
    public function testGetArtist(): void
    {
        $response = $this->music->getArtist("3941697");
        $this->assertEquals('Blink', $response['artistName']);
    }
}