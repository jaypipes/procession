// Code generated by protoc-gen-go.
// source: user.proto
// DO NOT EDIT!

package procession

import proto "github.com/golang/protobuf/proto"
import fmt "fmt"
import math "math"

// Reference imports to suppress errors if they are not otherwise used.
var _ = proto.Marshal
var _ = fmt.Errorf
var _ = math.Inf

// Basic information about a user of the system
type User struct {
	Uuid        string `protobuf:"bytes,1,opt,name=uuid" json:"uuid,omitempty"`
	DisplayName string `protobuf:"bytes,2,opt,name=display_name,json=displayName" json:"display_name,omitempty"`
	Email       string `protobuf:"bytes,3,opt,name=email" json:"email,omitempty"`
	Generation  uint32 `protobuf:"varint,100,opt,name=generation" json:"generation,omitempty"`
}

func (m *User) Reset()                    { *m = User{} }
func (m *User) String() string            { return proto.CompactTextString(m) }
func (*User) ProtoMessage()               {}
func (*User) Descriptor() ([]byte, []int) { return fileDescriptor9, []int{0} }

func (m *User) GetUuid() string {
	if m != nil {
		return m.Uuid
	}
	return ""
}

func (m *User) GetDisplayName() string {
	if m != nil {
		return m.DisplayName
	}
	return ""
}

func (m *User) GetEmail() string {
	if m != nil {
		return m.Email
	}
	return ""
}

func (m *User) GetGeneration() uint32 {
	if m != nil {
		return m.Generation
	}
	return 0
}

type GetUserRequest struct {
	Session  *Session `protobuf:"bytes,1,opt,name=session" json:"session,omitempty"`
	UserUuid string   `protobuf:"bytes,2,opt,name=user_uuid,json=userUuid" json:"user_uuid,omitempty"`
}

func (m *GetUserRequest) Reset()                    { *m = GetUserRequest{} }
func (m *GetUserRequest) String() string            { return proto.CompactTextString(m) }
func (*GetUserRequest) ProtoMessage()               {}
func (*GetUserRequest) Descriptor() ([]byte, []int) { return fileDescriptor9, []int{1} }

func (m *GetUserRequest) GetSession() *Session {
	if m != nil {
		return m.Session
	}
	return nil
}

func (m *GetUserRequest) GetUserUuid() string {
	if m != nil {
		return m.UserUuid
	}
	return ""
}

type SetUserRequest struct {
	Session *Session `protobuf:"bytes,1,opt,name=session" json:"session,omitempty"`
	User    *User    `protobuf:"bytes,2,opt,name=user" json:"user,omitempty"`
}

func (m *SetUserRequest) Reset()                    { *m = SetUserRequest{} }
func (m *SetUserRequest) String() string            { return proto.CompactTextString(m) }
func (*SetUserRequest) ProtoMessage()               {}
func (*SetUserRequest) Descriptor() ([]byte, []int) { return fileDescriptor9, []int{2} }

func (m *SetUserRequest) GetSession() *Session {
	if m != nil {
		return m.Session
	}
	return nil
}

func (m *SetUserRequest) GetUser() *User {
	if m != nil {
		return m.User
	}
	return nil
}

type SearchUsersFilters struct {
	Uuids     []string `protobuf:"bytes,1,rep,name=uuids" json:"uuids,omitempty"`
	NamesLike []string `protobuf:"bytes,2,rep,name=names_like,json=namesLike" json:"names_like,omitempty"`
	Emails    []string `protobuf:"bytes,3,rep,name=emails" json:"emails,omitempty"`
}

func (m *SearchUsersFilters) Reset()                    { *m = SearchUsersFilters{} }
func (m *SearchUsersFilters) String() string            { return proto.CompactTextString(m) }
func (*SearchUsersFilters) ProtoMessage()               {}
func (*SearchUsersFilters) Descriptor() ([]byte, []int) { return fileDescriptor9, []int{3} }

func (m *SearchUsersFilters) GetUuids() []string {
	if m != nil {
		return m.Uuids
	}
	return nil
}

func (m *SearchUsersFilters) GetNamesLike() []string {
	if m != nil {
		return m.NamesLike
	}
	return nil
}

func (m *SearchUsersFilters) GetEmails() []string {
	if m != nil {
		return m.Emails
	}
	return nil
}

type SearchUsersRequest struct {
	Filters *SearchUsersFilters `protobuf:"bytes,1,opt,name=filters" json:"filters,omitempty"`
	Options *SearchOptions      `protobuf:"bytes,2,opt,name=options" json:"options,omitempty"`
}

func (m *SearchUsersRequest) Reset()                    { *m = SearchUsersRequest{} }
func (m *SearchUsersRequest) String() string            { return proto.CompactTextString(m) }
func (*SearchUsersRequest) ProtoMessage()               {}
func (*SearchUsersRequest) Descriptor() ([]byte, []int) { return fileDescriptor9, []int{4} }

func (m *SearchUsersRequest) GetFilters() *SearchUsersFilters {
	if m != nil {
		return m.Filters
	}
	return nil
}

func (m *SearchUsersRequest) GetOptions() *SearchOptions {
	if m != nil {
		return m.Options
	}
	return nil
}

func init() {
	proto.RegisterType((*User)(nil), "procession.User")
	proto.RegisterType((*GetUserRequest)(nil), "procession.GetUserRequest")
	proto.RegisterType((*SetUserRequest)(nil), "procession.SetUserRequest")
	proto.RegisterType((*SearchUsersFilters)(nil), "procession.SearchUsersFilters")
	proto.RegisterType((*SearchUsersRequest)(nil), "procession.SearchUsersRequest")
}

func init() { proto.RegisterFile("user.proto", fileDescriptor9) }

var fileDescriptor9 = []byte{
	// 327 bytes of a gzipped FileDescriptorProto
	0x1f, 0x8b, 0x08, 0x00, 0x00, 0x09, 0x6e, 0x88, 0x02, 0xff, 0xa4, 0x52, 0x4d, 0x4f, 0xc2, 0x40,
	0x10, 0x4d, 0x05, 0x41, 0x86, 0x8f, 0x98, 0xd5, 0x98, 0x8a, 0x91, 0x60, 0xe3, 0x81, 0x8b, 0x1c,
	0xe0, 0xe2, 0x2f, 0xd0, 0x8b, 0xd1, 0xa4, 0x84, 0x9b, 0x09, 0x59, 0xe9, 0xa8, 0x1b, 0x4a, 0xb7,
	0xee, 0xb4, 0x07, 0xcf, 0xfe, 0x71, 0x33, 0xb3, 0x6d, 0x04, 0x3d, 0x7a, 0x82, 0x79, 0xef, 0x75,
	0xe6, 0xbd, 0xd7, 0x02, 0x94, 0x84, 0x6e, 0x9a, 0x3b, 0x5b, 0x58, 0x05, 0xb9, 0xb3, 0x6b, 0x24,
	0x32, 0x36, 0x1b, 0xf6, 0x08, 0xb5, 0x5b, 0xbf, 0x7b, 0x66, 0xd8, 0x27, 0x0f, 0xfb, 0x31, 0x22,
	0x68, 0x2e, 0x09, 0x9d, 0x52, 0xd0, 0x2c, 0x4b, 0x93, 0x84, 0xc1, 0x38, 0x98, 0x74, 0x62, 0xf9,
	0xaf, 0xae, 0xa0, 0x97, 0x18, 0xca, 0x53, 0xfd, 0xb9, 0xca, 0xf4, 0x16, 0xc3, 0x03, 0xe1, 0xba,
	0x15, 0xf6, 0xa8, 0xb7, 0xa8, 0x4e, 0xe1, 0x10, 0xb7, 0xda, 0xa4, 0x61, 0x43, 0x38, 0x3f, 0xa8,
	0x11, 0xc0, 0x1b, 0x66, 0xe8, 0x74, 0x61, 0x6c, 0x16, 0x26, 0xe3, 0x60, 0xd2, 0x8f, 0x77, 0x90,
	0xe8, 0x19, 0x06, 0xf7, 0x58, 0xf0, 0xdd, 0x18, 0x3f, 0x4a, 0xa4, 0x42, 0xdd, 0x40, 0xbb, 0xf2,
	0x25, 0x0e, 0xba, 0xb3, 0x93, 0xe9, 0x4f, 0x82, 0xe9, 0xc2, 0xff, 0xc6, 0xb5, 0x46, 0x5d, 0x40,
	0x87, 0xc3, 0xae, 0xc4, 0xb2, 0xb7, 0x75, 0xc4, 0xc0, 0xb2, 0x34, 0x49, 0x84, 0x30, 0x58, 0xfc,
	0x6b, 0xfb, 0x35, 0x34, 0x79, 0x99, 0x2c, 0xee, 0xce, 0x8e, 0x77, 0xb5, 0xb2, 0x55, 0xd8, 0x48,
	0x83, 0x5a, 0x48, 0xb1, 0x8c, 0xd1, 0x9d, 0x49, 0x0b, 0x74, 0xc4, 0x85, 0xb0, 0x29, 0x0a, 0x83,
	0x71, 0x83, 0x0b, 0x91, 0x41, 0x5d, 0x02, 0x70, 0x83, 0xb4, 0x4a, 0xcd, 0x86, 0x7b, 0x64, 0xaa,
	0x23, 0xc8, 0x83, 0xd9, 0xa0, 0x3a, 0x83, 0x96, 0x14, 0x47, 0x61, 0x43, 0xa8, 0x6a, 0x8a, 0xbe,
	0x82, 0xbd, 0x1b, 0x75, 0x9c, 0x5b, 0x68, 0xbf, 0xfa, 0x73, 0x55, 0x9c, 0xd1, 0x7e, 0x9c, 0xdf,
	0xa6, 0xe2, 0x5a, 0xae, 0xe6, 0xd0, 0xb6, 0x39, 0xbf, 0x02, 0xaa, 0xc2, 0x9d, 0xff, 0x7d, 0xf2,
	0xc9, 0x0b, 0xe2, 0x5a, 0xf9, 0xd2, 0x92, 0x2f, 0x65, 0xfe, 0x1d, 0x00, 0x00, 0xff, 0xff, 0xc0,
	0x3b, 0xb3, 0x26, 0x60, 0x02, 0x00, 0x00,
}
