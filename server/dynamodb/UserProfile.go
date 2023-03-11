package dynamodb

import (
	"errors"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"

	"fmt"
	"log"
)

type User struct {
	Name string `json:"name"`
	UserId string `json:"userId"`
	MasterPlayListId string `json:"masterPlayListId"`
	MasterPlayListName string `json:"masterPlayListName"`
}

const (
	tableName string = "User"
)

func GetUserDetails(userId string) (*User, error) {
	client := getDynamoDBClient()

	result, err := client.GetItem(&dynamodb.GetItemInput{
		TableName: aws.String(tableName),
		Key: map[string]*dynamodb.AttributeValue{
			"userId": {
				S: aws.String(userId),
			},
		},
	})

	if err != nil {
		log.Fatalf("Got error calling GetItem: %s", err)
	}

	if result.Item == nil {
		msg := "could not find '" + userId + "'"
		return nil, errors.New(msg)
	}
		
	user := User{}

	err = dynamodbattribute.UnmarshalMap(result.Item, &user)
	if err != nil {
		panic(fmt.Sprintf("Failed to unmarshal Record, %v", err))
	}

	return &user, nil

}

func UpdateUserDetails() {
	client := getDynamoDBClient()

	user := User{
		Name: "Test",
		MasterPlayListId: "1293129",
		UserId: "2132",
		MasterPlayListName: "Master",
	}
	av, err := dynamodbattribute.MarshalMap(user)
	if err != nil {
		panic(fmt.Sprintf("failed to DynamoDB marshal Record, %v", err))
	}
	
	_, err = client.PutItem(&dynamodb.PutItemInput{
		TableName: aws.String(tableName),
		Item:      av,
	})

	if err != nil {
		panic(fmt.Sprintf("failed to put Record to DynamoDB, %v", err))
	} else {
		fmt.Printf("Successfully added user details for user %s in DynamoDB", user.UserId)
	}
}
