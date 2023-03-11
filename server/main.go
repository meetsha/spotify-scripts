package main

import (
	"fmt"
	"net/http"
	"os/exec"
	"github.com/gin-gonic/gin"
)

func masterPlaylistHandler(c *gin.Context) {
	fmt.Print("hanlder called!")
	test := exec.Command("python", "../python_scripts/test.py")
	output, err := test.Output()


	if err != nil {
		fmt.Print("Error occured calling python!")
		fmt.Print(err.Error())
	}

	fmt.Print(string(output))

	c.IndentedJSON(http.StatusOK, "Hey there! First REST API in Go")
}

func main() {
	router := gin.Default()
	router.GET("/create-master-playlist", masterPlaylistHandler)

	router.Run("localhost:8080")
	http.Handle("/", http.FileServer(http.Dir("./static")))
	http.ListenAndServe("localhost:3000", nil)
}
