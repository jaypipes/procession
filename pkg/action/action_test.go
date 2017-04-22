package action

import (
    "fmt"
    "testing"

    pb "github.com/jaypipes/procession/proto"
)

func TestFailure(t *testing.T) {
    err := fmt.Errorf("Big time fail!")
    message := Failure(err)
    if message == nil {
        t.Error("Expected a pointer to pb.ActionReply. Got nil.")
    }
    if message.NumRecordsChanged != 0 {
        t.Errorf(
            "Expected no records changed. Got %d.",
            message.NumRecordsChanged,
        )
    }
    if message.Result != pb.ActionResult_FAILURE {
        t.Errorf(
            "Expected a FAILURE(1) result. Got %d",
            message.Result,
        )
    }
    if len(message.Errors) != 1 {
        t.Errorf(
            "Expected one error in response. Got %d.",
            len(message.Errors),
        )
    }
    gotErr := message.Errors[0]
    if gotErr.FaultCode != 127 {
        t.Errorf(
            "Expected a 127 fault code. Got %d",
            gotErr.FaultCode,
        )
    }
}


func TestSuccess(t *testing.T) {
    recordsChanged := uint32(42)
    message := Success(recordsChanged)
    if message == nil {
        t.Error("Expected a pointer to pb.ActionReply. Got nil.")
    }
    if message.NumRecordsChanged != recordsChanged {
        t.Errorf(
            "Expected %d records changed. Got %d.",
            recordsChanged,
            message.NumRecordsChanged,
        )
    }
    if message.Result != pb.ActionResult_SUCCESS {
        t.Errorf(
            "Expected a SUCCESS(0) result. Got %d",
            message.Result,
        )
    }
    if len(message.Errors) != 0 {
        t.Errorf(
            "Expected no errors in response. Got %d.",
            len(message.Errors),
        )
    }
}
