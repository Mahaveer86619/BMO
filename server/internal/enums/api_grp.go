package enums

type ApiGroup string

const (
	ApiGroupV1 ApiGroup = "/api/v1"
)

func (g ApiGroup) String() string {
	return string(g)
}
