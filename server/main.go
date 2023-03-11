package main

import (
	"fmt"
	"net/http"
	"os/exec"
	"github.com/gin-gonic/gin"
)

func masterPlaylistHandler(c *gin.Context) {
	test := exec.Command("python test.py")
	_, err := test.Output()

	if err != nil {
		fmt.Print(err.Error())
	}
	
	c.IndentedJSON(http.StatusOK, "Hey there! First REST API in Go")
}

func main() {
	router := gin.Default()
	router.GET("/create-master-playlist", masterPlaylistHandler)

	router.Run("localhost:8080")
	http.Handle("/", http.FileServer(http.Dir("./static")))
	http.ListenAndServe("localhost:3000", nil)
}
