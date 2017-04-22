package action

import (
	pb "github.com/jaypipes/procession/proto"
)

func Failure(err error) *pb.ActionReply {
	errMsg := pb.Error{
        FaultCode: 127,
        ErrorText: err.Error(),
    }
	result := &pb.ActionReply{
        Result: pb.ActionResult_FAILURE,
        NumRecordsChanged: 0,
    }
	result.Errors = append(result.Errors, &errMsg)
	return result
}

func Success(numChanged uint32) *pb.ActionReply {
	return &pb.ActionReply{
        Result: pb.ActionResult_SUCCESS,
        NumRecordsChanged: numChanged,
    }
}
