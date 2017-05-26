// Code generated by protoc-gen-go.
// source: common.proto
// DO NOT EDIT!

/*
Package procession is a generated protocol buffer package.

It is generated from these files:
	common.proto
	organization.proto
	search.proto
	service_iam.proto
	session.proto
	user.proto
	wrappers.proto

It has these top-level messages:
	Error
	ActionReply
	Organization
	OrganizationGetRequest
	OrganizationSetFields
	OrganizationSetRequest
	OrganizationSetResponse
	OrganizationListFilters
	OrganizationListRequest
	OrganizationMembersSetRequest
	OrganizationMembersSetResponse
	OrganizationMembersListRequest
	OrganizationDeleteRequest
	OrganizationDeleteResponse
	SearchOptions
	Session
	User
	UserGetRequest
	UserSetFields
	UserSetRequest
	UserSetResponse
	UserListFilters
	UserListRequest
	UserMembersListRequest
	UserDeleteRequest
	UserDeleteResponse
	DoubleValue
	FloatValue
	Int64Value
	UInt64Value
	Int32Value
	UInt32Value
	BoolValue
	StringValue
	BytesValue
*/
package procession

import proto "github.com/golang/protobuf/proto"
import fmt "fmt"
import math "math"

// Reference imports to suppress errors if they are not otherwise used.
var _ = proto.Marshal
var _ = fmt.Errorf
var _ = math.Inf

// This is a compile-time assertion to ensure that this generated file
// is compatible with the proto package it is being compiled against.
// A compilation error at this line likely means your copy of the
// proto package needs to be updated.
const _ = proto.ProtoPackageIsVersion2 // please upgrade the proto package

type ActionResult int32

const (
	ActionResult_SUCCESS         ActionResult = 0
	ActionResult_FAILURE         ActionResult = 1
	ActionResult_PARTIAL_FAILURE ActionResult = 2
)

var ActionResult_name = map[int32]string{
	0: "SUCCESS",
	1: "FAILURE",
	2: "PARTIAL_FAILURE",
}
var ActionResult_value = map[string]int32{
	"SUCCESS":         0,
	"FAILURE":         1,
	"PARTIAL_FAILURE": 2,
}

func (x ActionResult) String() string {
	return proto.EnumName(ActionResult_name, int32(x))
}
func (ActionResult) EnumDescriptor() ([]byte, []int) { return fileDescriptor0, []int{0} }

// Information about individual errors that may have occurred
type Error struct {
	FaultCode uint32 `protobuf:"varint,1,opt,name=fault_code,json=faultCode" json:"fault_code,omitempty"`
	ErrorText string `protobuf:"bytes,2,opt,name=error_text,json=errorText" json:"error_text,omitempty"`
}

func (m *Error) Reset()                    { *m = Error{} }
func (m *Error) String() string            { return proto.CompactTextString(m) }
func (*Error) ProtoMessage()               {}
func (*Error) Descriptor() ([]byte, []int) { return fileDescriptor0, []int{0} }

func (m *Error) GetFaultCode() uint32 {
	if m != nil {
		return m.FaultCode
	}
	return 0
}

func (m *Error) GetErrorText() string {
	if m != nil {
		return m.ErrorText
	}
	return ""
}

// Returned from gRPC calls that create, update or delete a set of records
type ActionReply struct {
	Result            ActionResult `protobuf:"varint,1,opt,name=result,enum=procession.ActionResult" json:"result,omitempty"`
	NumRecordsChanged uint32       `protobuf:"varint,2,opt,name=num_records_changed,json=numRecordsChanged" json:"num_records_changed,omitempty"`
	Errors            []*Error     `protobuf:"bytes,10,rep,name=errors" json:"errors,omitempty"`
}

func (m *ActionReply) Reset()                    { *m = ActionReply{} }
func (m *ActionReply) String() string            { return proto.CompactTextString(m) }
func (*ActionReply) ProtoMessage()               {}
func (*ActionReply) Descriptor() ([]byte, []int) { return fileDescriptor0, []int{1} }

func (m *ActionReply) GetResult() ActionResult {
	if m != nil {
		return m.Result
	}
	return ActionResult_SUCCESS
}

func (m *ActionReply) GetNumRecordsChanged() uint32 {
	if m != nil {
		return m.NumRecordsChanged
	}
	return 0
}

func (m *ActionReply) GetErrors() []*Error {
	if m != nil {
		return m.Errors
	}
	return nil
}

func init() {
	proto.RegisterType((*Error)(nil), "procession.Error")
	proto.RegisterType((*ActionReply)(nil), "procession.ActionReply")
	proto.RegisterEnum("procession.ActionResult", ActionResult_name, ActionResult_value)
}

func init() { proto.RegisterFile("common.proto", fileDescriptor0) }

var fileDescriptor0 = []byte{
	// 253 bytes of a gzipped FileDescriptorProto
	0x1f, 0x8b, 0x08, 0x00, 0x00, 0x09, 0x6e, 0x88, 0x02, 0xff, 0x4c, 0x90, 0xc1, 0x4b, 0xc3, 0x30,
	0x14, 0x87, 0xcd, 0xc4, 0x4a, 0x5f, 0x37, 0xdd, 0xb2, 0x4b, 0x2f, 0x42, 0xd9, 0xa9, 0x7a, 0x28,
	0x32, 0xcf, 0x1e, 0x4a, 0xa9, 0x30, 0xd8, 0x41, 0xd2, 0xed, 0x1c, 0x66, 0xfa, 0xd4, 0x41, 0x9b,
	0x57, 0x92, 0x14, 0xe6, 0xbf, 0xe2, 0x5f, 0x2b, 0xcd, 0x36, 0xdc, 0x31, 0xbf, 0xef, 0x23, 0x1f,
	0x09, 0x8c, 0x15, 0xb5, 0x2d, 0xe9, 0xac, 0x33, 0xe4, 0x88, 0x43, 0x67, 0x48, 0xa1, 0xb5, 0x7b,
	0xd2, 0x8b, 0x12, 0x6e, 0x4a, 0x63, 0xc8, 0xf0, 0x07, 0x80, 0xcf, 0x5d, 0xdf, 0x38, 0xa9, 0xa8,
	0xc6, 0x98, 0x25, 0x2c, 0x9d, 0x88, 0xd0, 0x2f, 0x05, 0xd5, 0x38, 0x60, 0x1c, 0x3c, 0xe9, 0xf0,
	0xe0, 0xe2, 0x51, 0xc2, 0xd2, 0x50, 0x84, 0x7e, 0xd9, 0xe0, 0xc1, 0x2d, 0x7e, 0x19, 0x44, 0xb9,
	0x72, 0x7b, 0xd2, 0x02, 0xbb, 0xe6, 0x87, 0x3f, 0x43, 0x60, 0xd0, 0xf6, 0x8d, 0xf3, 0x37, 0xdd,
	0x2d, 0xe3, 0xec, 0xbf, 0x99, 0x9d, 0xc5, 0x81, 0x8b, 0x93, 0xc7, 0x33, 0x98, 0xeb, 0xbe, 0x95,
	0x06, 0x15, 0x99, 0xda, 0x4a, 0xf5, 0xbd, 0xd3, 0x5f, 0x58, 0xfb, 0xd2, 0x44, 0xcc, 0x74, 0xdf,
	0x8a, 0x23, 0x29, 0x8e, 0x80, 0x3f, 0x42, 0xe0, 0xf3, 0x36, 0x86, 0xe4, 0x3a, 0x8d, 0x96, 0xb3,
	0xcb, 0x82, 0x7f, 0x92, 0x38, 0x09, 0x4f, 0xaf, 0x30, 0xbe, 0x4c, 0xf2, 0x08, 0x6e, 0xab, 0x6d,
	0x51, 0x94, 0x55, 0x35, 0xbd, 0x1a, 0x0e, 0x6f, 0xf9, 0x6a, 0xbd, 0x15, 0xe5, 0x94, 0xf1, 0x39,
	0xdc, 0xbf, 0xe7, 0x62, 0xb3, 0xca, 0xd7, 0xf2, 0x3c, 0x8e, 0x3e, 0x02, 0xff, 0x6b, 0x2f, 0x7f,
	0x01, 0x00, 0x00, 0xff, 0xff, 0xb2, 0x4f, 0x95, 0x99, 0x45, 0x01, 0x00, 0x00,
}
